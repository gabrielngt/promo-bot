import os
import threading
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Annotated

from database import (
    get_all_products, delete_product, get_price_history,
    get_settings, update_settings, upsert_product, set_watch, set_target, clear_discovered,
    get_status, watch_product, get_active_coupons, get_sales_summary, get_sales_series, get_recent_orders,
)
from aliexpress import extract_product_id, get_product_detail
from monitor import run_check

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

app = FastAPI(title="Promo Bot API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_auth(key: str = Security(api_key_header)):
    if not ADMIN_API_KEY:
        raise HTTPException(500, "ADMIN_API_KEY not configured on server")
    if key != ADMIN_API_KEY:
        raise HTTPException(401, "Invalid API key")
    return key


# ---------- Health ----------

@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.get("/api/health")
def health(key: str = Security(require_auth)):
    return {"status": "ok"}


@app.get("/api/status")
def status(key: str = Security(require_auth)):
    s = get_settings()
    st = get_status()
    st["monitoring_enabled"] = s["monitoring_enabled"]
    st["filters_enabled"] = s["filters_enabled"]
    st["check_interval_minutes"] = s["check_interval_minutes"]
    return st


@app.post("/api/run")
def trigger_run(key: str = Security(require_auth)):
    # dispara em background: um ciclo leva minutos e não pode travar a resposta.
    # run_check tem lock próprio, então um disparo durante outro ciclo é no-op.
    threading.Thread(target=run_check, daemon=True).start()
    return {"message": "Verificação disparada"}


# ---------- Products ----------

@app.get("/api/products")
def list_products(key: str = Security(require_auth)):
    products = get_all_products()
    for p in products:
        if p["min_price"] and p["last_price"]:
            drop = (p["min_price"] - p["last_price"]) / p["min_price"] * 100
            p["drop_pct"] = round(drop, 1)
        else:
            p["drop_pct"] = 0.0
    return products


@app.get("/api/products/{product_id}/history")
def product_history(product_id: str, key: str = Security(require_auth)):
    return get_price_history(product_id)


class AddProductRequest(BaseModel):
    url_or_id: str
    target_price: float | None = None


@app.post("/api/products", status_code=201)
def add_product(body: AddProductRequest, key: str = Security(require_auth)):
    pid = extract_product_id(body.url_or_id)
    if not pid:
        raise HTTPException(400, "URL ou ID inválido")

    product = get_product_detail(pid)
    if not product:
        raise HTTPException(404, "Produto não encontrado.")

    upsert_product(product["product_id"], product["title"], product["price"], product.get("link", ""))
    set_watch(product["product_id"], body.target_price)
    return {"message": "Produto adicionado à watchlist", "product": product}


@app.delete("/api/products/discovered")
def clear_discovered_products(key: str = Security(require_auth)):
    n = clear_discovered()
    return {"message": f"{n} produtos descobertos removidos", "deleted": n}


class TargetRequest(BaseModel):
    target_price: float | None = None


@app.put("/api/products/{product_id}/target")
def update_target(product_id: str, body: TargetRequest, key: str = Security(require_auth)):
    set_target(product_id, body.target_price)
    return {"message": "Preço-alvo atualizado", "target_price": body.target_price}


@app.put("/api/products/{product_id}/watch")
def watch(product_id: str, key: str = Security(require_auth)):
    if not watch_product(product_id):
        raise HTTPException(404, "Produto não encontrado")
    return {"message": "Produto adicionado à watchlist"}


@app.delete("/api/products/{product_id}")
def remove_product(product_id: str, key: str = Security(require_auth)):
    if not delete_product(product_id):
        raise HTTPException(404, "Produto não encontrado")
    return {"message": "Produto removido"}


@app.get("/api/coupons")
def list_coupons(key: str = Security(require_auth)):
    """Cupons de campanha descobertos automaticamente nos anúncios (últimas 72h)."""
    return get_active_coupons()


# ---------- Vendas ----------

@app.get("/api/sales")
def sales(days: int = 30, key: str = Security(require_auth)):
    return {
        "summary": get_sales_summary(days),
        "series": get_sales_series(days),
        "orders": get_recent_orders(50),
    }


# ---------- Settings ----------

@app.get("/api/settings")
def read_settings(key: str = Security(require_auth)):
    return get_settings()


class SettingsRequest(BaseModel):
    price_drop_threshold:   Annotated[float, Field(gt=0, le=1)] | None = None
    cold_start_threshold:   Annotated[float, Field(gt=0, le=1)] | None = None
    check_interval_minutes: Annotated[int,   Field(ge=1)]       | None = None
    min_repost_days:        Annotated[int,   Field(ge=0)]       | None = None
    max_posts_per_cycle:    Annotated[int,   Field(ge=1)]       | None = None
    peripheral_keywords:    list[str] | None = None
    brand_whitelist:        list[str] | None = None
    keyword_blacklist:      list[str] | None = None
    monitoring_enabled:     bool | None = None
    filters_enabled:        bool | None = None
    import_tax_rate:        Annotated[float, Field(ge=0, le=1)] | None = None
    icms_rate:              Annotated[float, Field(ge=0, lt=1)] | None = None
    coupon_campaigns:       list[str] | None = None


@app.put("/api/settings")
def write_settings(body: SettingsRequest, key: str = Security(require_auth)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(400, "Nenhum campo enviado")
    update_settings(data)
    return get_settings()
