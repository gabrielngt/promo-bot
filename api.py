import os
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    get_all_products, delete_product, get_price_history,
    get_settings, update_settings, upsert_product,
)
from aliexpress import extract_product_id, get_product_detail

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


@app.post("/api/products", status_code=201)
def add_product(body: AddProductRequest, key: str = Security(require_auth)):
    pid = extract_product_id(body.url_or_id)
    if not pid:
        raise HTTPException(400, "URL ou ID inválido")

    product = get_product_detail(pid)
    if not product:
        raise HTTPException(404, "Produto não encontrado. A busca por ID direto está indisponível temporariamente (aguardando aprovação da Advanced API). O scheduler descobre produtos automaticamente pelas categorias a cada 60 min.")

    upsert_product(product["product_id"], product["title"], product["price"], product.get("link", ""))
    return {"message": "Produto adicionado", "product": product}


@app.delete("/api/products/{product_id}")
def remove_product(product_id: str, key: str = Security(require_auth)):
    if not delete_product(product_id):
        raise HTTPException(404, "Produto não encontrado")
    return {"message": "Produto removido"}


# ---------- Settings ----------

@app.get("/api/settings")
def read_settings(key: str = Security(require_auth)):
    return get_settings()


class SettingsRequest(BaseModel):
    price_drop_threshold: float | None = None
    cold_start_threshold: float | None = None
    check_interval_minutes: int | None = None
    min_repost_days: int | None = None
    peripheral_keywords: list[str] | None = None
    brand_whitelist: list[str] | None = None
    keyword_blacklist: list[str] | None = None


@app.put("/api/settings")
def write_settings(body: SettingsRequest, key: str = Security(require_auth)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(400, "Nenhum campo enviado")
    update_settings(data)
    return get_settings()
