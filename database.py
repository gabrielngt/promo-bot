import sqlite3
from datetime import datetime, timedelta
from config import MIN_REPOST_DAYS

DB_PATH = "promo_bot.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                product_id      TEXT PRIMARY KEY,
                title           TEXT,
                min_price       REAL,
                last_price      REAL,
                last_checked    TEXT,
                posted_at       TEXT
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  TEXT,
                price       REAL,
                checked_at  TEXT
            );
        """)


def upsert_product(product_id: str, title: str, price: float) -> dict:
    """
    Inserts or updates a product. Returns a dict with:
      - is_new: bool
      - min_price: float (historical minimum before this update)
      - last_price: float
    """
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO products (product_id, title, min_price, last_price, last_checked) VALUES (?, ?, ?, ?, ?)",
                (product_id, title, price, price, now),
            )
            conn.execute(
                "INSERT INTO price_history (product_id, price, checked_at) VALUES (?, ?, ?)",
                (product_id, price, now),
            )
            return {"is_new": True, "min_price": price, "last_price": price}

        min_price = min(row["min_price"], price)
        conn.execute(
            "UPDATE products SET title=?, min_price=?, last_price=?, last_checked=? WHERE product_id=?",
            (title, min_price, price, now, product_id),
        )
        conn.execute(
            "INSERT INTO price_history (product_id, price, checked_at) VALUES (?, ?, ?)",
            (product_id, price, now),
        )
        return {"is_new": False, "min_price": row["min_price"], "last_price": row["last_price"]}


def can_post(product_id: str) -> bool:
    """Returns True if the product hasn't been posted recently."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT posted_at FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        if not row or not row["posted_at"]:
            return True
        posted_at = datetime.fromisoformat(row["posted_at"])
        return datetime.utcnow() - posted_at > timedelta(days=MIN_REPOST_DAYS)


def mark_posted(product_id: str):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE products SET posted_at=? WHERE product_id=?", (now, product_id)
        )
