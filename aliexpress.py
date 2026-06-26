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


def generate_affiliate_links(urls: list[str]) -> dict[str, str]:
    """Converte até 50 URLs em links de afiliado rastreáveis. Retorna {url_original: url_afiliado}."""
    if not urls:
        return {}
    params = _base_params("aliexpress.affiliate.link.generate")
    params.update({
        "tracking_id": ALIEXPRESS_TRACKING_ID,
        "source_values": ",".join(urls[:50]),
        "promotion_link_type": "0",
    })
    params["sign"] = _sign(params)
    try:
        resp = requests.post(API_URL, data=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "error_response" in data:
            print(f"[AliExpress] link.generate error: {data['error_response']}")
            return {}
        result = (
            data
            .get("aliexpress_affiliate_link_generate_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            print(f"[AliExpress] link.generate: {result.get('resp_msg')}")
            return {}
        links = result.get("result", {}).get("promotion_links", {}).get("promotion_link", [])
        if isinstance(links, dict):
            links = [links]
        return {lk["source_value"]: lk["promotion_url"] for lk in links if lk.get("promotion_url")}
    except Exception as e:
        print(f"[AliExpress] Exceção em link.generate: {e}")
        return {}


def _extract_products(result: dict) -> list:
    """Aceita products:[...] (formato do doc) e products:{product:[...]} (gateway real)."""
    prods = result.get("result", {}).get("products", [])
    if isinstance(prods, dict):
        prods = prods.get("product", [])
    return prods or []


def _ensure_affiliate_links(products: list) -> list:
    """Garante promotion_link rastreável; gera via link.generate para os que faltarem."""
    needs_link = [
        (i, raw.get("product_detail_url", f"https://www.aliexpress.com/item/{raw.get('product_id')}.html"))
        for i, raw in enumerate(products)
        if not raw.get("promotion_link")
    ]
    if needs_link:
        link_map = generate_affiliate_links([url for _, url in needs_link])
        for i, url in needs_link:
            if url in link_map:
                products[i]["promotion_link"] = link_map[url]
    return products


def get_products_by_brand(brand: str, page_size: int = 50) -> list[dict]:
    """Busca produtos de uma marca por keyword (product.query — busca geral)."""
    return _query_products(keywords=brand, page_size=page_size)


def search_products(keywords: str, page_size: int = 20) -> list[dict]:
    """Busca anúncios por texto livre — usado para achar equivalentes de um produto vigiado."""
    return _query_products(keywords=keywords, page_size=page_size)


def _query_products(keywords: str = "", page: int = 1, page_size: int = 50) -> list[dict]:
    """Standard API: aliexpress.affiliate.product.query (busca por keyword)."""
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
        return _ensure_affiliate_links(_extract_products(result))
    except Exception as e:
        print(f"[AliExpress] Exceção em product.query: {e}")
        return []


def get_hot_products(category_id: str, page: int = 1, page_size: int = 50) -> list[dict]:
    """Advanced API: aliexpress.affiliate.hotproduct.query — produtos em alta por categoria."""
    params = _base_params("aliexpress.affiliate.hotproduct.query")
    params.update({
        "category_ids": category_id,
        "tracking_id": ALIEXPRESS_TRACKING_ID,
        "page_no": str(page),
        "page_size": str(page_size),
        "target_currency": "BRL",
        "target_language": "PT",
        "sort": "LAST_VOLUME_DESC",
    })
    params["sign"] = _sign(params)
    try:
        resp = requests.post(API_URL, data=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "error_response" in data:
            print(f"[AliExpress] hotproduct.query error: {data['error_response']}")
            return []
        result = (
            data
            .get("aliexpress_affiliate_hotproduct_query_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            print(f"[AliExpress] hotproduct.query categoria {category_id}: {result.get('resp_msg')}")
            return []
        return _ensure_affiliate_links(_extract_products(result))
    except Exception as e:
        print(f"[AliExpress] Exceção em hotproduct.query ({category_id}): {e}")
        return []


def get_product_detail(product_id: str) -> dict | None:
    """Advanced API: aliexpress.affiliate.productdetail.get — busca exata por ID."""
    params = _base_params("aliexpress.affiliate.productdetail.get")
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
        if "error_response" in data:
            print(f"[AliExpress] productdetail.get error: {data['error_response']}")
            return None
        result = (
            data
            .get("aliexpress_affiliate_productdetail_get_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            print(f"[AliExpress] productdetail.get {product_id}: {result.get('resp_msg')}")
            return None
        products = _ensure_affiliate_links(_extract_products(result))
        return parse_product(products[0]) if products else None
    except Exception as e:
        print(f"[AliExpress] Exceção em productdetail.get ({product_id}): {e}")
        return None


def get_shipping(product_id: str, sku_id: str, sale_price: float) -> dict | None:
    """Frete + prazo para o Brasil. Retorna {fee, min_days, max_days} ou None."""
    if not sku_id:
        return None
    params = _base_params("aliexpress.affiliate.product.shipping.get")
    params.update({
        "product_id": str(product_id),
        "sku_id": str(sku_id),
        "ship_to_country": "BR",
        "target_currency": "BRL",
        "target_sale_price": f"{sale_price:.2f}",
        "target_language": "PT",
        "tax_rate": "0",
    })
    params["sign"] = _sign(params)
    try:
        resp = requests.post(API_URL, data=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "error_response" in data:
            print(f"[AliExpress] shipping.get error: {data['error_response']}")
            return None
        result = (
            data
            .get("aliexpress_affiliate_product_shipping_get_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            return None
        r = result.get("result", {})
        if not r:
            return None

        def _days(v):
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return None

        return {
            "fee": _parse_price(r.get("shipping_fee") or "0"),
            "min_days": _days(r.get("min_delivery_days")),
            "max_days": _days(r.get("max_delivery_days") or r.get("delivery_days")),
        }
    except Exception as e:
        print(f"[AliExpress] Exceção em shipping.get ({product_id}): {e}")
        return None


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


def _parse_coupon(raw: dict, price: float) -> dict | None:
    """Extrai cupom do promo_code_info. Calcula o preço final quando o desconto é fixo."""
    import re
    info = raw.get("promo_code_info") or {}
    code = info.get("promo_code")
    if not code:
        return None
    desc = info.get("code_value", "")
    min_spend = _parse_price(info.get("code_mini_spend") or "0")
    # desconto fixo descrito como "... get BRL 28.19 off" (cupons em % são só exibidos)
    discount = 0.0
    if "%" not in desc:
        m = re.search(r"get\s+[A-Za-z]{0,3}\s*([\d.,]+)\s*off", desc, re.IGNORECASE)
        if m:
            discount = _parse_price(m.group(1))
    applicable = discount > 0 and price >= min_spend
    return {
        "code": code,
        "discount": discount,
        "min_spend": min_spend,
        "applicable": applicable,
        "final_price": round(price - discount, 2) if applicable else price,
    }


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

        coupon = _parse_coupon(raw, price)

        return {
            "product_id": product_id,
            "sku_id": str(raw.get("sku_id", "")),
            "title": title,
            "price": price,
            "original_price": original_price,
            "discount_pct": float(discount) if discount else 0.0,
            "coupon": coupon,
            "link": promotion_link,
            "image_url": image_url,
            "rating": float(rating) / 20 if rating else 0.0,
            "sales": int(sales),
        }
    except Exception as e:
        print(f"[AliExpress] Erro ao parsear produto {raw.get('product_id')}: {e}")
        return None
