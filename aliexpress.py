import hashlib
import time
import requests
from config import ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET, ALIEXPRESS_TRACKING_ID

API_URL = "https://api-sg.aliexpress.com/sync"


def _parse_price(value) -> float:
    """Converts API price string to float. Handles '99.90', '99.90 BRL', '1,299.90'."""
    import re
    s = str(value).strip()
    # extrai só dígitos, ponto e vírgula
    match = re.search(r"[\d,\.]+", s)
    if not match:
        return 0.0
    num = match.group()
    # se tiver tanto ponto quanto vírgula, o último separador é o decimal
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


def get_hot_products(category_id: str, page: int = 1, page_size: int = 50) -> list[dict]:
    """Returns hot/promoted products for a category with affiliate links."""
    params = _base_params("aliexpress.affiliate.hotproduct.query")
    params.update({
        "category_id": category_id,
        "tracking_id": ALIEXPRESS_TRACKING_ID,
        "page_no": str(page),
        "page_size": str(page_size),
        "target_currency": "BRL",
        "target_language": "PT",
        "sort": "LAST_VOLUME_DESC",  # ordena por vendas recentes
    })
    params["sign"] = _sign(params)

    try:
        resp = requests.post(API_URL, data=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        result = (
            data
            .get("aliexpress_affiliate_hotproduct_query_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            print(f"[AliExpress] Erro na categoria {category_id}: {result.get('resp_msg')}")
            return []
        return result.get("result", {}).get("products", {}).get("product", [])
    except Exception as e:
        print(f"[AliExpress] Exceção na categoria {category_id}: {e}")
        return []


def extract_product_id(url_or_id: str) -> str | None:
    """Extracts AliExpress product ID from a URL or returns the ID directly."""
    import re
    s = url_or_id.strip()
    # já é um ID numérico
    if re.fullmatch(r"\d+", s):
        return s
    # URL padrão: /item/1005006789012345.html
    match = re.search(r"/item/(\d+)", s)
    if match:
        return match.group(1)
    # URL mobile: /i/1005006789012345.html
    match = re.search(r"/i/(\d+)", s)
    if match:
        return match.group(1)
    return None


def get_product_detail(product_id: str) -> dict | None:
    """Fetches a single product by ID from AliExpress Portals API."""
    params = _base_params("aliexpress.affiliate.product.detail.get")
    params.update({
        "product_ids": product_id,
        "tracking_id": ALIEXPRESS_TRACKING_ID,
        "target_currency": "BRL",
        "target_language": "PT",
    })
    params["sign"] = _sign(params)

    try:
        resp = requests.post(API_URL, data=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        print(f"[AliExpress] raw response keys: {list(data.keys())}")
        result = (
            data
            .get("aliexpress_affiliate_product_detail_get_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            print(f"[AliExpress] product detail error: {result}")
            return None
        products = result.get("result", {}).get("products", {}).get("product", [])
        if not products:
            return None
        return parse_product(products[0])
    except Exception as e:
        print(f"[AliExpress] Erro ao buscar produto {product_id}: {e}")
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
            "rating": float(rating) / 20 if rating else 0.0,  # converte 0-100 → 0-5
            "sales": int(sales),
        }
    except Exception as e:
        print(f"[AliExpress] Erro ao parsear produto {raw.get('product_id')}: {e}")
        return None
