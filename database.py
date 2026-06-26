import os
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

_DEFAULTS = {
    "price_drop_threshold": "0.05",
    "cold_start_threshold": "0.30",
    "check_interval_minutes": "10",
    "min_repost_days": "1",
    "max_posts_per_cycle": "5",
    "peripheral_keywords": "",  # populated from config on first init
    "brand_whitelist": "",  # vazio = sem filtro de marca
    "keyword_blacklist": "",  # produtos cujo título contiver qualquer palavra são ignorados
}


def get_connection():
    # prepare_threshold=None desliga prepared statements no lado do cliente,
    # necessário para o transaction pooler do Supabase (porta 6543), que reusa
    # conexões entre transações. Inofensivo no session pooler.
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None)


def init_db(keyword_defaults: list[str] | None = None):
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id          TEXT PRIMARY KEY,
                title               TEXT,
                min_price           REAL,
                last_price          REAL,
                last_checked        TEXT,
                posted_at           TEXT,
                last_posted_price   REAL,
                link                TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id          BIGSERIAL PRIMARY KEY,
                product_id  TEXT,
                price       REAL,
                checked_at  TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT
            )
        """)
        conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS last_posted_price REAL")
        conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS link TEXT DEFAULT ''")
        conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS is_watched BOOLEAN DEFAULT FALSE")
        conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS target_price REAL")
        defaults = dict(_DEFAULTS)
        if keyword_defaults:
            defaults["peripheral_keywords"] = "\n".join(keyword_defaults)
        for k, v in defaults.items():
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
                (k, v)
            )


# ---------- Settings ----------

def _parse_brand_entry(line: str) -> dict:
    if ":" in line:
        name, _, kws_str = line.partition(":")
        keywords = [k.strip() for k in kws_str.split(",") if k.strip()]
    else:
        name, keywords = line, []
    return {"name": name.strip(), "keywords": keywords}


def get_settings() -> dict:
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    s = {r["key"]: r["value"] for r in rows}
    return {
        "price_drop_threshold": float(s.get("price_drop_threshold", 0.15)),
        "cold_start_threshold": float(s.get("cold_start_threshold", 0.30)),
        "check_interval_minutes": int(s.get("check_interval_minutes", 60)),
        "min_repost_days": int(s.get("min_repost_days", 3)),
        "max_posts_per_cycle": int(s.get("max_posts_per_cycle", 5)),
        "peripheral_keywords": [
            kw.strip() for kw in s.get("peripheral_keywords", "").splitlines() if kw.strip()
        ],
        "brand_whitelist": [
            _parse_brand_entry(b)
            for b in s.get("brand_whitelist", "").splitlines()
            if b.strip()
        ],
        "keyword_blacklist": [
            kw.strip() for kw in s.get("keyword_blacklist", "").splitlines() if kw.strip()
        ],
    }


def update_settings(data: dict):
    with get_connection() as conn:
        for k, v in data.items():
            if k in ("peripheral_keywords", "brand_whitelist", "keyword_blacklist") and isinstance(v, list):
                v = "\n".join(v)
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (k, str(v))
            )


# ---------- Products ----------

def upsert_product(product_id: str, title: str, price: float, link: str = "") -> dict:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE product_id = %s", (product_id,)
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO products (product_id, title, min_price, last_price, last_checked, link) VALUES (%s, %s, %s, %s, %s, %s)",
                (product_id, title, price, price, now, link),
            )
            conn.execute(
                "INSERT INTO price_history (product_id, price, checked_at) VALUES (%s, %s, %s)",
                (product_id, price, now),
            )
            return {"is_new": True, "min_price": price, "last_price": price}

        min_price = min(row["min_price"], price)
        conn.execute(
            "UPDATE products SET title=%s, min_price=%s, last_price=%s, last_checked=%s, link=%s WHERE product_id=%s",
            (title, min_price, price, now, link or row["link"], product_id),
        )
        conn.execute(
            "INSERT INTO price_history (product_id, price, checked_at) VALUES (%s, %s, %s)",
            (product_id, price, now),
        )
        return {"is_new": False, "min_price": row["min_price"], "last_price": row["last_price"]}


def can_post(product_id: str, current_price: float = 0.0) -> bool:
    settings = get_settings()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT posted_at, last_posted_price FROM products WHERE product_id = %s", (product_id,)
        ).fetchone()
        if not row or not row["posted_at"]:
            return True
        posted_at = datetime.fromisoformat(row["posted_at"])
        elapsed = datetime.utcnow() - posted_at
        last_price = row["last_posted_price"]

        if last_price and abs(current_price - last_price) < 0.01 and elapsed < timedelta(hours=12):
            return False

        return elapsed > timedelta(days=settings["min_repost_days"])


def mark_posted(product_id: str, price: float = 0.0):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE products SET posted_at=%s, last_posted_price=%s WHERE product_id=%s",
            (now, price, product_id),
        )


def get_all_products() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT product_id, title, min_price, last_price, last_checked, posted_at, link, "
            "is_watched, target_price "
            "FROM products ORDER BY last_checked DESC"
        ).fetchall()
    return list(rows)


def set_watch(product_id: str, target_price: float | None = None):
    with get_connection() as conn:
        conn.execute(
            "UPDATE products SET is_watched = TRUE, target_price = %s WHERE product_id = %s",
            (target_price, product_id),
        )


def get_watchlist() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT product_id, title, min_price, last_price, target_price "
            "FROM products WHERE is_watched = TRUE ORDER BY title"
        ).fetchall()
    return list(rows)


def delete_product(product_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        conn.execute("DELETE FROM price_history WHERE product_id = %s", (product_id,))
    return cur.rowcount > 0


def clear_discovered() -> int:
    """Remove todos os produtos auto-descobertos (não vigiados), mantendo a watchlist."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM price_history WHERE product_id IN "
            "(SELECT product_id FROM products WHERE is_watched IS NOT TRUE)"
        )
        cur = conn.execute("DELETE FROM products WHERE is_watched IS NOT TRUE")
    return cur.rowcount


def get_price_history(product_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT price, checked_at FROM price_history WHERE product_id = %s ORDER BY checked_at",
            (product_id,),
        ).fetchall()
    return list(rows)
