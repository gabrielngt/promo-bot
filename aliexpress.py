import hashlib
import time
import requests
from config import ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET, ALIEXPRESS_TRACKING_ID

API_URL = "https://api-sg.aliexpress.com/sync"


def _parse_price(value) -> float:
    """Converts API price string to float. Handles '99.90', '99.90 BRL', '1,299.90'."""
    import re
    s = str(value).strip()
    match = re.search(r"[\d,\.]+", s)
    if not match:
        return 0.0
    num = match.group()
    if "," in num and "." in num:
        if num.rindex(",") > num.rindex("."):
            num = num.replace(".", "").replace(",", ".")  # formato BR: 1.299,90
        else:
            num = num.replace(",", "")  # formato US: 1,299.90
    else:
        num = num.replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return 0.0


def _sign(params: dict) -> str:
    sorted_pairs = sorted(params.items())
    concat = "".join(f"{k}{v}" for k, v in sorted_pairs)
    sign_str = ALIEXPRESS_APP_SECRET + concat + ALIEXPRESS_APP_SECRET
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()


def _base_params(method: str) -> dict:
    return {
        "method": method,
        "app_key": ALIEXPRESS_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "format": "json",
        "v": "2.0",
        "sign_method": "md5",
    }


# ── WORKAROUND (Standard API) ─────────────────────────────────────────────────
# Remover quando Advanced API for aprovada e descomentar os métodos abaixo.

def get_products_by_brand(brand: str, page_size: int = 50) -> list[dict]:
    """Busca produtos de uma marca específica como keyword."""
    return _query_products(keywords=brand, page_size=page_size)


def _query_products(keywords: str = "", category_id: str = "", page: int = 1, page_size: int = 50) -> list[dict]:
    """Standard API: aliexpress.affiliate.product.query"""
    params = _base_params("aliexpress.affiliate.product.query")
    params.update({
        "tracking_id": ALIEXPRESS_TRACKING_ID,
        "page_no": str(page),
        "page_size": str(page_size),
        "target_currency": "BRL",
        "target_language": "PT",
        "sort": "LAST_VOLUME_DESC",
    })
    if keywords:
        params["keywords"] = keywords
    if category_id:
        params["category_ids"] = category_id
    params["sign"] = _sign(params)
    try:
        resp = requests.post(API_URL, data=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "error_response" in data:
            print(f"[AliExpress] product.query error: {data['error_response']}")
            return []
        result = (
            data
            .get("aliexpress_affiliate_product_query_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            print(f"[AliExpress] product.query: {result.get('resp_msg')}")
            return []
        return result.get("result", {}).get("products", {}).get("product", [])
    except Exception as e:
        print(f"[AliExpress] Exceção em product.query: {e}")
        return []


def get_hot_products(category_id: str, page: int = 1, page_size: int = 50) -> list[dict]:
    # WORKAROUND: Standard API via product.query por categoria.
    # Quando Advanced API for aprovada, substituir pelo bloco comentado abaixo:
    #
    # params = _base_params("aliexpress.affiliate.hotproduct.query")
    # params.update({
    #     "category_id": category_id,
    #     "tracking_id": ALIEXPRESS_TRACKING_ID,
    #     "page_no": str(page),
    #     "page_size": str(page_size),
    #     "target_currency": "BRL",
    #     "target_language": "PT",
    #     "sort": "LAST_VOLUME_DESC",
    # })
    # params["sign"] = _sign(params)
    # try:
    #     resp = requests.post(API_URL, data=params, timeout=15)
    #     resp.raise_for_status()
    #     data = resp.json()
    #     if "error_response" in data:
    #         print(f"[AliExpress] hotproduct API error: {data['error_response']}")
    #         return []
    #     result = (
    #         data
    #         .get("aliexpress_affiliate_hotproduct_query_response", {})
    #         .get("resp_result", {})
    #     )
    #     if result.get("resp_code") != 200:
    #         print(f"[AliExpress] Erro na categoria {category_id}: {result.get('resp_msg')}")
    #         return []
    #     return result.get("result", {}).get("products", {}).get("product", [])
    # except Exception as e:
    #     print(f"[AliExpress] Exceção na categoria {category_id}: {e}")
    #     return []
    return _query_products(category_id=category_id, page=page, page_size=page_size)


def get_product_detail(product_id: str) -> dict | None:
    # WORKAROUND: busca via product.query usando o ID como keyword.
    # Quando Advanced API for aprovada, substituir pelo bloco comentado abaixo:
    #
    # params = _base_params("aliexpress.affiliate.product.detail.get")
    # params.update({
    #     "product_ids": product_id,
    #     "tracking_id": ALIEXPRESS_TRACKING_ID,
    #     "target_currency": "BRL",
    #     "target_language": "PT",
    # })
    # params["sign"] = _sign(params)
    # try:
    #     resp = requests.post(API_URL, data=params, timeout=15)
    #     resp.raise_for_status()
    #     data = resp.json()
    #     if "error_response" in data:
    #         print(f"[AliExpress] product detail API error: {data['error_response']}")
    #         return None
    #     result = (
    #         data
    #         .get("aliexpress_affiliate_product_detail_get_response", {})
    #         .get("resp_result", {})
    #     )
    #     if result.get("resp_code") != 200:
    #         print(f"[AliExpress] product detail error: {result}")
    #         return None
    #     products = result.get("result", {}).get("products", {}).get("product", [])
    #     if not products:
    #         return None
    #     return parse_product(products[0])
    # except Exception as e:
    #     print(f"[AliExpress] Erro ao buscar produto {product_id}: {e}")
    #     return None
    products = _query_products(keywords=product_id, page_size=20)
    for raw in products:
        if str(raw.get("product_id")) == product_id:
            return parse_product(raw)
    return None

# ─────────────────────────────────────────────────────────────────────────────


def extract_product_id(url_or_id: str) -> str | None:
    """Extracts AliExpress product ID from a URL or returns the ID directly."""
    import re
    s = url_or_id.strip()
    if re.fullmatch(r"\d+", s):
        return s
    match = re.search(r"/item/(\d+)", s)
    if match:
        return match.group(1)
    match = re.search(r"/i/(\d+)", s)
    if match:
        return match.group(1)
    return None


def parse_product(raw: dict) -> dict | None:
    """Normaliza um produto da API para o formato interno."""
    try:
        product_id = str(raw["product_id"])
        title = raw.get("product_title", "")
        price_str = raw.get("target_sale_price") or raw.get("sale_price") or "0"
        price = _parse_price(price_str)
        original_str = raw.get("target_original_price") or raw.get("original_price") or price_str
        original_price = _parse_price(original_str)
        discount = raw.get("discount", "0%").replace("%", "")
        promotion_link = raw.get("promotion_link") or raw.get("product_detail_url", "")
        image_url = raw.get("product_main_image_url", "")
        rating = raw.get("evaluate_rate", "0%").replace("%", "")
        sales = raw.get("lastest_volume", 0)
        return {
            "product_id": product_id,
            "title": title,
            "price": price,
            "original_price": original_price,
            "discount_pct": float(discount) if discount else 0.0,
            "link": promotion_link,
            "image_url": image_url,
            "rating": float(rating) / 20 if rating else 0.0,
            "sales": int(sales),
        }
    except Exception as e:
        print(f"[AliExpress] Erro ao parsear produto {raw.get('product_id')}: {e}")
        return None
