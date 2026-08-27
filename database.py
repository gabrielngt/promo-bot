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
    # teto diário: o limite por ciclo não segura nada sozinho (com intervalo de
    # 10 min são ~144 ciclos/dia). Protege o canal de flood quando algo faz
    # muitos produtos parecerem em promoção ao mesmo tempo.
    "max_posts_per_day": "20",
    "peripheral_keywords": "",  # populated from config on first init
    "brand_whitelist": "",  # vazio = sem filtro de marca
    # Marcas da Shopee: a whitelist da AliExpress é de marcas chinesas de
    # entusiasta que quase não existem no varejo nacional, então a Shopee tem a
    # sua. Padrão validado contra a API (marcas com volume e nota reais).
    "shopee_brand_whitelist": "\n".join([
        "lenovo", "razer", "havit", "aula", "redragon",
        "fortrek", "knup", "husky", "rise mode",
    ]),
    "keyword_blacklist": "",  # produtos cujo título contiver qualquer palavra são ignorados
    "monitoring_enabled": "1",  # chave-mestra: desligado = scheduler não busca/posta
    "filters_enabled": "1",  # desligado = ignora keyword/blacklist/marca (listas ficam salvas)
    # tributos somados pelo AliExpress no checkout (o preço da API vem sem eles):
    # total = (preço + frete) × (1 + II) ÷ (1 − ICMS)
    "import_tax_rate": "0",  # II federal — zerado pela MP de mai/2026 para compras ≤ US$50
    "icms_rate": "0.17",  # ICMS cobrado "por dentro" (17–20% conforme o estado)
    # cupons de campanha ativos (a API não os lista; cole do portal de afiliados)
    # um por linha: CODIGO gasto_minimo desconto — ex: "BRT28 141 28"
    "coupon_campaigns": "",
}


def _as_bool(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on")


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
    # vendas: payload cru (p/ investigar campos não documentados) e exclusão manual
    "ALTER TABLE affiliate_orders ADD COLUMN IF NOT EXISTS raw_json TEXT",
    "ALTER TABLE affiliate_orders ADD COLUMN IF NOT EXISTS excluded BOOLEAN DEFAULT FALSE",
    # cupons: origem (auto/manual) e validade explícita
    "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'auto'",
    "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS expires_at timestamptz",
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coupons (
                code        TEXT PRIMARY KEY,
                min_spend   double precision NOT NULL,
                discount    double precision NOT NULL,
                last_seen   timestamptz NOT NULL,
                source      TEXT DEFAULT 'auto',
                expires_at  timestamptz
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS affiliate_orders (
                order_id              TEXT NOT NULL,
                sub_order_id          TEXT NOT NULL,
                product_id            TEXT,
                product_title         TEXT,
                order_status          TEXT,
                paid_amount           double precision,
                commission_rate       TEXT,
                estimated_commission  double precision,
                currency              TEXT,
                order_date            DATE,
                created_time_raw      TEXT,
                paid_time_raw         TEXT,
                is_new_buyer          BOOLEAN,
                raw_json              TEXT,
                excluded              BOOLEAN DEFAULT FALSE,
                synced_at             timestamptz NOT NULL,
                PRIMARY KEY (order_id, sub_order_id)
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
        _migrate_campaign_setting(conn)


def _migrate_campaign_setting(conn):
    """Cupons manuais moraram num campo de texto em settings; agora são linhas na
    tabela coupons (com validade). Move o que houver e esvazia o campo."""
    row = conn.execute("SELECT value FROM settings WHERE key='coupon_campaigns'").fetchone()
    if not row or not (row["value"] or "").strip():
        return
    moved = 0
    for line in row["value"].splitlines():
        c = _parse_campaign_entry(line)
        if not c:
            continue
        conn.execute(
            "INSERT INTO coupons (code, min_spend, discount, last_seen, source) "
            "VALUES (%s, %s, %s, %s, 'manual') ON CONFLICT (code) DO NOTHING",
            (c["code"], c["min_spend"], c["discount"], _utcnow()),
        )
        moved += 1
    conn.execute("UPDATE settings SET value='' WHERE key='coupon_campaigns'")
    if moved:
        print(f"[DB] {moved} cupom(ns) migrado(s) do campo de texto para a tabela.")


# ---------- Settings ----------

def _num(s: str) -> float:
    """'141' / '141,00' / 'R$1.299,90' → float. Levanta ValueError se não for número."""
    s = s.strip().lstrip("Rr$ ").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    return float(s)


def _parse_campaign_entry(line: str) -> dict | None:
    """Extrai {code, min_spend, discount} de uma linha em formato livre.
    Aceita "BRT28 141 28" e também texto colado do portal, tipo
    "Código BRT28 — compras acima de R$ 141,00: R$ 28,00 OFF" ou uma linha de
    central de cupons com validade ("AFS3 $3 off $15 2026-08-26 23:59:59").
    Heurística do formato livre: remove data/hora de validade (senão o ano vira
    "o maior número da linha" e é lido como gasto mínimo); código = token com
    letras E números; gasto mínimo = maior valor restante; desconto = segundo maior."""
    import re
    line = re.sub(r"\d{4}-\d{1,2}-\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?", " ", line)
    line = re.sub(r"\b\d{1,2}:\d{2}:\d{2}\b", " ", line)
    parts = line.split()
    if len(parts) == 3:
        try:
            return {"code": parts[0], "min_spend": _num(parts[1]), "discount": _num(parts[2])}
        except ValueError:
            pass
    code = None
    for t in parts:
        tok = t.strip(".,:;()|—-")
        if (len(tok) >= 4 and re.search(r"[A-Za-z]", tok) and re.search(r"\d", tok)
                and not tok.upper().startswith("R$")):
            code = tok
            break
    if not code:
        return None
    nums = []
    for n in re.findall(r"\d+(?:[.,]\d{1,2})?", line.replace(code, " ")):
        try:
            v = _num(n)
        except ValueError:
            continue
        if v > 0:
            nums.append(v)
    if len(nums) < 2:
        return None
    nums.sort(reverse=True)
    min_spend, discount = nums[0], nums[1]
    if discount >= min_spend:
        return None
    return {"code": code, "min_spend": min_spend, "discount": discount}


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
        "max_posts_per_day": int(s.get("max_posts_per_day", 20)),
        "peripheral_keywords": [
            kw.strip() for kw in s.get("peripheral_keywords", "").splitlines() if kw.strip()
        ],
        "brand_whitelist": [
            _parse_brand_entry(b)
            for b in s.get("brand_whitelist", "").splitlines()
            if b.strip()
        ],
        # só nomes de marca (sem o formato "marca:keywords" da AliExpress)
        "shopee_brand_whitelist": [
            {"name": b.strip(), "keywords": []}
            for b in s.get("shopee_brand_whitelist", "").splitlines()
            if b.strip()
        ],
        "keyword_blacklist": [
            kw.strip() for kw in s.get("keyword_blacklist", "").splitlines() if kw.strip()
        ],
        "monitoring_enabled": _as_bool(s.get("monitoring_enabled", "1")),
        "filters_enabled": _as_bool(s.get("filters_enabled", "1")),
        "import_tax_rate": float(s.get("import_tax_rate", 0.0)),
        "icms_rate": float(s.get("icms_rate", 0.17)),
    }


def update_settings(data: dict):
    with get_connection() as conn:
        for k, v in data.items():
            if k in ("peripheral_keywords", "brand_whitelist", "keyword_blacklist",
                     "coupon_campaigns", "shopee_brand_whitelist") and isinstance(v, list):
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


def count_posts_since(hours: int = 24) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM products WHERE posted_at >= %s",
            (_utcnow() - timedelta(hours=hours),),
        ).fetchone()
    return row["n"] if row else 0


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


def watch_product(product_id: str) -> bool:
    """Promove um produto já existente (descoberto) para a watchlist, sem tocar no alvo."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE products SET is_watched = TRUE WHERE product_id = %s", (product_id,)
        )
    return cur.rowcount > 0


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


# ---------- Cupons descobertos ----------
# Cupons de campanha são globais (o mesmo código vale em vários produtos), então
# todo cupom visto num anúncio é guardado e reaplicado nos demais posts.

def save_coupon(code: str, min_spend: float, discount: float):
    """Cupom colhido automaticamente de um anúncio. Não mexe em cupom manual
    (o usuário definiu valores e validade à mão)."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO coupons (code, min_spend, discount, last_seen, source) "
            "VALUES (%s, %s, %s, %s, 'auto') "
            "ON CONFLICT (code) DO UPDATE SET min_spend=EXCLUDED.min_spend, "
            "discount=EXCLUDED.discount, last_seen=EXCLUDED.last_seen "
            "WHERE coupons.source IS DISTINCT FROM 'manual'",
            (code, min_spend, discount, _utcnow()),
        )


def add_manual_coupon(code: str, min_spend: float, discount: float, expires_at=None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO coupons (code, min_spend, discount, last_seen, source, expires_at) "
            "VALUES (%s, %s, %s, %s, 'manual', %s) "
            "ON CONFLICT (code) DO UPDATE SET min_spend=EXCLUDED.min_spend, "
            "discount=EXCLUDED.discount, source='manual', expires_at=EXCLUDED.expires_at, "
            "last_seen=EXCLUDED.last_seen",
            (code, min_spend, discount, _utcnow(), expires_at),
        )


def delete_coupon(code: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM coupons WHERE code = %s", (code,))
    return cur.rowcount > 0


# Um cupom vale enquanto: (manual) a validade não passou — sem validade = sempre;
# (auto) foi visto nas últimas N horas, já que campanhas somem sem aviso.
_ACTIVE_SQL = """
    (source = 'manual' AND (expires_at IS NULL OR expires_at > %(now)s))
    OR (source IS DISTINCT FROM 'manual' AND last_seen >= %(cutoff)s)
"""


def get_active_coupons(max_age_hours: int = 72) -> list[dict]:
    """Cupons válidos agora — os manuais dentro da validade, os automáticos
    vistos nas últimas N horas."""
    params = {"now": _utcnow(), "cutoff": _utcnow() - timedelta(hours=max_age_hours)}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT code, min_spend, discount, last_seen, source, expires_at FROM coupons "
            f"WHERE {_ACTIVE_SQL} ORDER BY discount DESC", params,
        ).fetchall()
    return list(rows)


def list_coupons(max_age_hours: int = 72) -> list[dict]:
    """Para o painel: manuais (mesmo vencidos, p/ o usuário ver e remover) e os
    automáticos ainda válidos. Cada linha traz se está ativa."""
    params = {"now": _utcnow(), "cutoff": _utcnow() - timedelta(hours=max_age_hours)}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT code, min_spend, discount, last_seen, source, expires_at, "
            f"({_ACTIVE_SQL}) AS active FROM coupons "
            "WHERE source = 'manual' OR last_seen >= %(cutoff)s "
            "ORDER BY source DESC, discount DESC", params,
        ).fetchall()
    return list(rows)


# ---------- Vendas (pedidos de afiliado) ----------
# A comissão é liquidada numa moeda só (USD na conta atual), então os totais
# somam apenas a moeda dominante do período e informam qual é — somar moedas
# diferentes sem conversão daria um número sem significado.

def upsert_affiliate_order(o: dict):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO affiliate_orders (order_id, sub_order_id, product_id, product_title, "
            "order_status, paid_amount, commission_rate, estimated_commission, currency, "
            "order_date, created_time_raw, paid_time_raw, is_new_buyer, raw_json, synced_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (order_id, sub_order_id) DO UPDATE SET "
            "order_status=EXCLUDED.order_status, paid_amount=EXCLUDED.paid_amount, "
            "commission_rate=EXCLUDED.commission_rate, estimated_commission=EXCLUDED.estimated_commission, "
            "currency=EXCLUDED.currency, order_date=EXCLUDED.order_date, "
            "created_time_raw=EXCLUDED.created_time_raw, paid_time_raw=EXCLUDED.paid_time_raw, "
            "is_new_buyer=EXCLUDED.is_new_buyer, raw_json=EXCLUDED.raw_json, "
            "synced_at=EXCLUDED.synced_at",
            (o["order_id"], o["sub_order_id"], o.get("product_id"), o.get("product_title"),
             o.get("order_status"), o.get("paid_amount"), o.get("commission_rate"),
             o.get("estimated_commission"), o.get("currency"), o.get("order_date"),
             o.get("created_time_raw"), o.get("paid_time_raw"), o.get("is_new_buyer"),
             o.get("raw_json"), _utcnow()),
        )


def get_dominant_currency(days: int = 30) -> str | None:
    """Moeda com maior volume no período — os totais somam só ela."""
    cutoff = (_utcnow() - timedelta(days=days)).date()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT currency FROM affiliate_orders WHERE order_date >= %s AND excluded IS NOT TRUE "
            "GROUP BY currency ORDER BY SUM(paid_amount) DESC NULLS LAST LIMIT 1",
            (cutoff,),
        ).fetchone()
    return row["currency"] if row else None


def get_sales_summary(days: int = 30) -> dict:
    cutoff = (_utcnow() - timedelta(days=days)).date()
    currency = get_dominant_currency(days)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count, COALESCE(SUM(paid_amount),0) AS paid_total, "
            "COALESCE(SUM(estimated_commission),0) AS commission_total "
            "FROM affiliate_orders WHERE order_date >= %s AND currency IS NOT DISTINCT FROM %s "
            "AND excluded IS NOT TRUE",
            (cutoff, currency),
        ).fetchone()
    return {
        "days": days,
        "currency": currency,
        "count": row["count"],
        "paid_total": row["paid_total"],
        "commission_total": row["commission_total"],
    }


def get_sales_series(days: int = 30) -> list[dict]:
    """Receita por dia na moeda dominante (só dias com pedido — o painel
    completa os dias vazios)."""
    cutoff = (_utcnow() - timedelta(days=days)).date()
    currency = get_dominant_currency(days)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT order_date, COUNT(*) AS count, COALESCE(SUM(paid_amount),0) AS paid_total "
            "FROM affiliate_orders WHERE order_date >= %s AND currency IS NOT DISTINCT FROM %s "
            "AND excluded IS NOT TRUE GROUP BY order_date ORDER BY order_date",
            (cutoff, currency),
        ).fetchall()
    return list(rows)


def get_recent_orders(limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT order_id, sub_order_id, product_id, product_title, order_status, "
            "paid_amount, estimated_commission, currency, order_date, excluded "
            "FROM affiliate_orders ORDER BY order_date DESC NULLS LAST, synced_at DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return list(rows)


# Cotação usada para exibir em BRL os valores que a AliExpress liquida em USD.
# Atualizada a cada sync (sales.py); o valor guardado é o fallback quando a
# consulta de câmbio falha.
_USD_BRL_FALLBACK = 5.40


def get_usd_brl_rate() -> float:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='usd_brl_rate'").fetchone()
    try:
        rate = float(row["value"]) if row and row["value"] else 0.0
    except (TypeError, ValueError):
        rate = 0.0
    return rate if rate > 0 else _USD_BRL_FALLBACK


def set_usd_brl_rate(rate: float):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('usd_brl_rate', %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (str(rate),),
        )


def set_order_excluded(order_id: str, sub_order_id: str, excluded: bool) -> bool:
    """Marca um pedido como não-comissionável (ex.: compra própria — a AliExpress
    não paga comissão nesses, mas a API os devolve junto com as vendas reais)."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE affiliate_orders SET excluded = %s WHERE order_id = %s AND sub_order_id = %s",
            (excluded, order_id, sub_order_id),
        )
    return cur.rowcount > 0


def record_check_run():
    """Marca o instante do último ciclo concluído (para o card de status do painel)."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('last_check_at', %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (_utcnow().isoformat(),),
        )


def get_status() -> dict:
    """Métricas leves para o painel: última verificação e contagens."""
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='last_check_at'").fetchone()
        last_check = row["value"] if row and row["value"] else None
        counts = conn.execute(
            "SELECT "
            "COUNT(*) FILTER (WHERE is_watched) AS watched, "
            "COUNT(*) FILTER (WHERE is_watched IS NOT TRUE) AS discovered, "
            "COUNT(*) FILTER (WHERE posted_at >= %s) AS posts_24h "
            "FROM products",
            (_utcnow() - timedelta(hours=24),),
        ).fetchone()
        # fallback p/ bancos anteriores ao record_check_run: usa a atividade real
        # (todo produto é tocado a cada ciclo), evitando "nunca" com posts existentes
        if last_check is None:
            r2 = conn.execute("SELECT MAX(last_checked) AS m FROM products").fetchone()
            if r2 and r2["m"]:
                last_check = r2["m"].isoformat()
    return {
        "last_check_at": last_check,
        "watched_count": counts["watched"],
        "discovered_count": counts["discovered"],
        "posts_24h": counts["posts_24h"],
    }


def prune_price_history(days: int = 90) -> int:
    """Apaga leituras antigas para o histórico não crescer sem limite.
    A janela de baseline do monitor é 30 dias; 90 dá folga com margem."""
    cutoff = _utcnow() - timedelta(days=days)
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM price_history WHERE checked_at < %s", (cutoff,))
    return cur.rowcount


def get_price_history(product_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT price, checked_at FROM price_history WHERE product_id = %s ORDER BY checked_at",
            (product_id,),
        ).fetchall()
    return list(rows)
