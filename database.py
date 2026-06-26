import os
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timedelta, timezone

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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_connection():
    # prepare_threshold=None desliga prepared statements no lado do cliente,
    # necessário para o transaction pooler do Supabase (porta 6543), que reusa
    # conexões entre transações. Inofensivo no session pooler.
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None)


# Migrações idempotentes para bancos que antecedem o schema atual. Os blocos DO
# checam o catálogo antes de agir, então rodam só uma vez e viram no-op (sem lock)
# nos boots seguintes. Bancos novos já nascem com os tipos certos no CREATE TABLE.
_TYPE_MIGRATION = """
DO $$
BEGIN
  -- preços: real (4 bytes) -> double precision (8 bytes)
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='products' AND column_name='min_price')='real' THEN
    ALTER TABLE products ALTER COLUMN min_price TYPE double precision;
  END IF;
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='products' AND column_name='last_price')='real' THEN
    ALTER TABLE products ALTER COLUMN last_price TYPE double precision;
  END IF;
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='products' AND column_name='last_posted_price')='real' THEN
    ALTER TABLE products ALTER COLUMN last_posted_price TYPE double precision;
  END IF;
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='products' AND column_name='target_price')='real' THEN
    ALTER TABLE products ALTER COLUMN target_price TYPE double precision;
  END IF;
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='price_history' AND column_name='price')='real' THEN
    ALTER TABLE price_history ALTER COLUMN price TYPE double precision;
  END IF;

  -- timestamps: text (ISO ingênuo, em UTC) -> timestamptz
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='products' AND column_name='last_checked')='text' THEN
    ALTER TABLE products ALTER COLUMN last_checked TYPE timestamptz USING (NULLIF(last_checked,'')::timestamp AT TIME ZONE 'UTC');
  END IF;
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='products' AND column_name='posted_at')='text' THEN
    ALTER TABLE products ALTER COLUMN posted_at TYPE timestamptz USING (NULLIF(posted_at,'')::timestamp AT TIME ZONE 'UTC');
  END IF;
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='price_history' AND column_name='checked_at')='text' THEN
    ALTER TABLE price_history ALTER COLUMN checked_at TYPE timestamptz USING (NULLIF(checked_at,'')::timestamp AT TIME ZONE 'UTC');
  END IF;

  -- NOT NULL no histórico (limpa nulos antes)
  IF (SELECT is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='price_history' AND column_name='product_id')='YES' THEN
    DELETE FROM price_history WHERE product_id IS NULL;
    ALTER TABLE price_history ALTER COLUMN product_id SET NOT NULL;
  END IF;
  IF (SELECT is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='price_history' AND column_name='price')='YES' THEN
    DELETE FROM price_history WHERE price IS NULL;
    ALTER TABLE price_history ALTER COLUMN price SET NOT NULL;
  END IF;
  IF (SELECT is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='price_history' AND column_name='checked_at')='YES' THEN
    DELETE FROM price_history WHERE checked_at IS NULL;
    ALTER TABLE price_history ALTER COLUMN checked_at SET NOT NULL;
  END IF;
END $$;
"""

_FK_MIGRATION = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fk_price_history_product') THEN
    DELETE FROM price_history WHERE product_id NOT IN (SELECT product_id FROM products);
    ALTER TABLE price_history ADD CONSTRAINT fk_price_history_product
      FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE;
  END IF;
END $$;
"""

_SCHEMA_MIGRATIONS = [
    # colunas para bancos anteriores à watchlist
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS last_posted_price double precision",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS link TEXT DEFAULT ''",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_watched BOOLEAN DEFAULT FALSE",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS target_price double precision",
    # acelera get_recent_min / get_price_history (filtram por product_id + checked_at)
    "CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history (product_id, checked_at)",
    _TYPE_MIGRATION,
    _FK_MIGRATION,
    # reações do Telegram
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS telegram_message_id BIGINT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS reactions_positive INT DEFAULT 0",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS reactions_negative INT DEFAULT 0",
]


def init_db(keyword_defaults: list[str] | None = None):
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id          TEXT PRIMARY KEY,
                title               TEXT,
                min_price           double precision,
                last_price          double precision,
                last_checked        timestamptz,
                posted_at           timestamptz,
                last_posted_price   double precision,
                link                TEXT DEFAULT '',
                is_watched          BOOLEAN DEFAULT FALSE,
                target_price        double precision
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id          BIGSERIAL PRIMARY KEY,
                product_id  TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
                price       double precision NOT NULL,
                checked_at  timestamptz NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT
            )
        """)
        for stmt in _SCHEMA_MIGRATIONS:
            conn.execute(stmt)
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
    now = _utcnow()
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
        posted_at = row["posted_at"]  # timestamptz -> datetime tz-aware
        elapsed = _utcnow() - posted_at
        last_price = row["last_posted_price"]

        if last_price and abs(current_price - last_price) < 0.01 and elapsed < timedelta(hours=12):
            return False

        return elapsed > timedelta(days=settings["min_repost_days"])


def mark_posted(product_id: str, price: float = 0.0, message_id: int | None = None):
    now = _utcnow()
    with get_connection() as conn:
        conn.execute(
            "UPDATE products SET posted_at=%s, last_posted_price=%s, telegram_message_id=%s WHERE product_id=%s",
            (now, price, message_id, product_id),
        )


def get_all_products() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT product_id, title, min_price, last_price, last_checked, posted_at, link, "
            "is_watched, target_price, telegram_message_id, reactions_positive, reactions_negative "
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


def set_target(product_id: str, target_price: float | None = None):
    with get_connection() as conn:
        conn.execute(
            "UPDATE products SET target_price = %s WHERE product_id = %s",
            (target_price, product_id),
        )


def get_recent_min(product_id: str, days: int = 30) -> float | None:
    """Menor preço registrado nos últimos N dias (janela móvel). None se sem histórico."""
    cutoff = _utcnow() - timedelta(days=days)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MIN(price) AS m FROM price_history "
            "WHERE product_id = %s AND checked_at >= %s",
            (product_id, cutoff),
        ).fetchone()
    return row["m"] if row and row["m"] is not None else None


def delete_product(product_id: str) -> bool:
    # price_history é removido em cascata pela FK
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
    return cur.rowcount > 0


def clear_discovered() -> int:
    """Remove todos os produtos auto-descobertos (não vigiados), mantendo a watchlist.
    O histórico de preços sai em cascata pela FK."""
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM products WHERE is_watched IS NOT TRUE")
    return cur.rowcount


def save_reactions(message_id: int, positive: int, negative: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE products SET reactions_positive=%s, reactions_negative=%s WHERE telegram_message_id=%s",
            (positive, negative, message_id),
        )


def get_reactions_offset() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='reactions_offset'").fetchone()
    return int(row["value"]) if row and row["value"] else 0


def set_reactions_offset(offset: int):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('reactions_offset', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (str(offset),)
        )


def get_price_history(product_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT price, checked_at FROM price_history WHERE product_id = %s ORDER BY checked_at",
            (product_id,),
        ).fetchall()
    return list(rows)
