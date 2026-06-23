import os
import sqlite3
from datetime import datetime, timedelta

def _resolve_db_path() -> str:
    if os.getenv("DB_PATH"):
        return os.getenv("DB_PATH")
    if os.path.isdir("/home"):
        return "/home/promo_bot.db"
    return "promo_bot.db"

DB_PATH = _resolve_db_path()

_DEFAULTS = {
    "price_drop_threshold": "0.15",
    "cold_start_threshold": "0.30",
    "check_interval_minutes": "10",
    "min_repost_days": "3",
    "max_posts_per_cycle": "5",
    "peripheral_keywords": "",  # populated from config on first init
    "brand_whitelist": "",  # vazio = sem filtro de marca
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(keyword_defaults: list[str] | None = None):
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                product_id          TEXT PRIMARY KEY,
                title               TEXT,
                min_price           REAL,
                last_price          REAL,
                last_checked        TEXT,
                posted_at           TEXT,
                last_posted_price   REAL,
                link                TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  TEXT,
                price       REAL,
                checked_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT
            );
        """)
        # migração segura para DBs existentes
        for col, definition in [("last_posted_price", "REAL"), ("link", "TEXT DEFAULT ''")]:
            try:
                conn.execute(f"ALTER TABLE products ADD COLUMN {col} {definition}")
            except Exception:
                pass
        # insere defaults apenas se ainda não existirem
        defaults = dict(_DEFAULTS)
        if keyword_defaults:
            defaults["peripheral_keywords"] = "\n".join(keyword_defaults)
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )


# ---------- Settings ----------

def get_settings() -> dict:
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    s = {r["key"]: r["value"] for r in rows}
    # converte tipos
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
            b.strip() for b in s.get("brand_whitelist", "").splitlines() if b.strip()
        ],
    }


def update_settings(data: dict):
    with get_connection() as conn:
        for k, v in data.items():
            if k in ("peripheral_keywords", "brand_whitelist") and isinstance(v, list):
                v = "\n".join(v)
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v))
            )


# ---------- Products ----------

def upsert_product(product_id: str, title: str, price: float, link: str = "") -> dict:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO products (product_id, title, min_price, last_price, last_checked, link) VALUES (?, ?, ?, ?, ?, ?)",
                (product_id, title, price, price, now, link),
            )
            conn.execute(
                "INSERT INTO price_history (product_id, price, checked_at) VALUES (?, ?, ?)",
                (product_id, price, now),
            )
            return {"is_new": True, "min_price": price, "last_price": price}

        min_price = min(row["min_price"], price)
        conn.execute(
            "UPDATE products SET title=?, min_price=?, last_price=?, last_checked=?, link=? WHERE product_id=?",
            (title, min_price, price, now, link or row["link"], product_id),
        )
        conn.execute(
            "INSERT INTO price_history (product_id, price, checked_at) VALUES (?, ?, ?)",
            (product_id, price, now),
        )
        return {"is_new": False, "min_price": row["min_price"], "last_price": row["last_price"]}


def can_post(product_id: str, current_price: float = 0.0) -> bool:
    settings = get_settings()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT posted_at, last_posted_price FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        if not row or not row["posted_at"]:
            return True
        posted_at = datetime.fromisoformat(row["posted_at"])
        elapsed = datetime.utcnow() - posted_at
        last_price = row["last_posted_price"]

        # mesmo preço nas últimas 12h → não reposta
        if last_price and abs(current_price - last_price) < 0.01 and elapsed < timedelta(hours=12):
            return False

        return elapsed > timedelta(days=settings["min_repost_days"])


def mark_posted(product_id: str, price: float = 0.0):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE products SET posted_at=?, last_posted_price=? WHERE product_id=?",
            (now, price, product_id),
        )


def get_all_products() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT product_id, title, min_price, last_price, last_checked, posted_at, link "
            "FROM products ORDER BY last_checked DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_product(product_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
    return cur.rowcount > 0


def get_price_history(product_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT price, checked_at FROM price_history WHERE product_id = ? ORDER BY checked_at",
            (product_id,),
        ).fetchall()
    return [dict(r) for r in rows]
