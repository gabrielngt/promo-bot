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
    elif re.fullmatch(r"\d{1,3}(,\d{3})+", num):
        num = num.replace(",", "")  # vírgula de milhar sem decimais: 1,299
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
        "ship_to_country": "BR",
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


def get_featured_promos() -> list[dict]:
    """Advanced API: aliexpress.affiliate.featuredpromo.get — campanhas promocionais ativas
    (Flash Deals, Choice Day etc.). Retorna [{promo_name, promo_desc, ...}]."""
    params = _base_params("aliexpress.affiliate.featuredpromo.get")
    params["tracking_id"] = ALIEXPRESS_TRACKING_ID
    params["sign"] = _sign(params)
    try:
        resp = requests.post(API_URL, data=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "error_response" in data:
            print(f"[AliExpress] featuredpromo.get error: {data['error_response']}")
            return []
        result = (
            data
            .get("aliexpress_affiliate_featuredpromo_get_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            print(f"[AliExpress] featuredpromo.get: {result.get('resp_msg')}")
            return []
        promos = result.get("result", {}).get("promos", [])
        if isinstance(promos, dict):
            promos = promos.get("promo", [])
        return promos or []
    except Exception as e:
        print(f"[AliExpress] Exceção em featuredpromo.get: {e}")
        return []


def get_featured_promo_products(promo_name: str, page: int = 1, page_size: int = 50) -> list[dict]:
    """Advanced API: aliexpress.affiliate.featuredpromo.products.get — produtos de uma campanha."""
    params = _base_params("aliexpress.affiliate.featuredpromo.products.get")
    params.update({
        "promotion_name": promo_name,
        "tracking_id": ALIEXPRESS_TRACKING_ID,
        "page_no": str(page),
        "page_size": str(page_size),
        "target_currency": "BRL",
        "target_language": "PT",
        "country": "BR",
    })
    params["sign"] = _sign(params)
    try:
        resp = requests.post(API_URL, data=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "error_response" in data:
            print(f"[AliExpress] featuredpromo.products.get error: {data['error_response']}")
            return []
        result = (
            data
            .get("aliexpress_affiliate_featuredpromo_products_get_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            print(f"[AliExpress] featuredpromo.products.get {promo_name}: {result.get('resp_msg')}")
            return []
        return _ensure_affiliate_links(_extract_products(result))
    except Exception as e:
        print(f"[AliExpress] Exceção em featuredpromo.products.get ({promo_name}): {e}")
        return []


def _extract_date(raw_time) -> str | None:
    """Extrai 'YYYY-MM-DD' do início de um timestamp em qualquer formato textual
    comum (ISO, 'yyyy-MM-dd HH:mm:ss'...). None se não reconhecer."""
    import re
    if not raw_time:
        return None
    m = re.match(r"\d{4}-\d{2}-\d{2}", str(raw_time).strip())
    return m.group() if m else None


def _parse_money_field(value) -> float:
    """Valores monetários de order.listbyindex vêm em CENTAVOS, como inteiro
    ("3792" = 37.92). Confirmado contra pedidos reais: paid_amount 3792 com
    commission_rate 3% devolve estimated_commission 113 (= 1.13).
    Se algum dia vier com separador decimal, já está em unidades — não divide."""
    import re
    s = str(value).strip()
    if re.search(r"[.,]\d", s):
        return _parse_price(s)
    return _parse_price(s) / 100


def _parse_order(raw: dict) -> dict | None:
    """Normaliza um pedido de aliexpress.affiliate.order.listbyindex. Prefere os
    campos 'finished_*' (valor/comissão já consolidados) e cai para 'paid_*'
    quando o pedido ainda não fechou."""
    try:
        order_id = str(raw["order_id"])
        amount = _parse_money_field(raw.get("finished_amount") or raw.get("paid_amount") or "0")
        commission = _parse_money_field(
            raw.get("estimated_finished_commission") or raw.get("estimated_paid_commission") or "0"
        )
        created_time = raw.get("created_time") or raw.get("paid_time")
        return {
            "order_id": order_id,
            "sub_order_id": str(raw.get("sub_order_id") or order_id),
            "product_id": str(raw.get("product_id", "")),
            "product_title": raw.get("product_title", ""),
            "order_status": raw.get("order_status", ""),
            "paid_amount": amount,
            "commission_rate": raw.get("commission_rate", ""),
            "estimated_commission": commission,
            "currency": raw.get("settled_currency") or "BRL",
            "order_date": _extract_date(created_time),
            "created_time_raw": str(created_time) if created_time else None,
            "paid_time_raw": str(raw.get("paid_time")) if raw.get("paid_time") else None,
            "is_new_buyer": str(raw.get("is_new_buyer", "")).strip().lower() in ("true", "1"),
        }
    except Exception as e:
        print(f"[AliExpress] Erro ao parsear pedido {raw.get('order_id')}: {e}")
        return None


def get_affiliate_orders(
    start_time: str, end_time: str, status: str, page_index: str | None = None, page_size: int = 50
) -> tuple[list[dict], str | None]:
    """Advanced API: aliexpress.affiliate.order.listbyindex — pedidos/comissões
    de afiliado num intervalo. status é obrigatório e não aceita múltiplos
    valores; consultar um de cada vez (ver sales.ORDER_STATUSES).

    NOTA: o formato de start_time/end_time não é fixado na documentação —
    assumido aqui como 'yyyy-MM-dd HH:mm:ss' (padrão comum nas APIs Alibaba).
    O nome do campo de paginação na resposta também não está confirmado
    (assumido 'start_query_index_id' ecoado de volta). Validar os dois com
    diagnose_api.py rodando no servidor antes de confiar cegamente na paginação
    além da primeira página.

    Retorna (pedidos_parseados, próximo_page_index) — próximo é None quando
    não há mais páginas (ou em erro)."""
    params = _base_params("aliexpress.affiliate.order.listbyindex")
    params.update({
        "start_time": start_time,
        "end_time": end_time,
        "status": status,
        "page_size": str(page_size),
    })
    if page_index:
        params["start_query_index_id"] = page_index
    params["sign"] = _sign(params)
    try:
        resp = requests.post(API_URL, data=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if "error_response" in data:
            print(f"[AliExpress] order.listbyindex error: {data['error_response']}")
            return [], None
        result = (
            data
            .get("aliexpress_affiliate_order_listbyindex_response", {})
            .get("resp_result", {})
        )
        if result.get("resp_code") != 200:
            print(f"[AliExpress] order.listbyindex ({status}): {result.get('resp_msg')}")
            return [], None
        r = result.get("result", {})
        raw_orders = r.get("orders", [])
        if isinstance(raw_orders, dict):
            raw_orders = raw_orders.get("order", [])
        raw_orders = raw_orders or []
        orders = [o for o in (_parse_order(x) for x in raw_orders) if o]
        # heurística de paginação (não confirmada — ver nota acima): menos
        # registros que o page_size pedido = última página.
        next_index = r.get("start_query_index_id") if len(raw_orders) >= page_size else None
        return orders, next_index
    except Exception as e:
        print(f"[AliExpress] Exceção em order.listbyindex: {e}")
        return [], None


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
    # link curto (s.click.aliexpress.com, a.aliexpress.com, etc.) — resolve redirect
    if s.startswith("http"):
        try:
            resp = requests.head(s, allow_redirects=True, timeout=5)
            m = re.search(r"/item/(\d+)", resp.url)
            if m:
                return m.group(1)
        except Exception:
            pass
    return None


def _parse_coupon(raw: dict, price: float) -> dict | None:
    """Extrai cupom do promo_code_info. O desconto vem como texto livre no
    code_value (a API não manda campo numérico), então é parseado por regex.
    Calcula o preço final para desconto fixo e percentual."""
    import re
    info = raw.get("promo_code_info") or {}
    code = info.get("promo_code")
    if not code:
        return None
    desc = info.get("code_value", "")
    min_spend = _parse_price(info.get("code_mini_spend") or "0")
    discount = 0.0
    if "%" in desc:
        # percentual: "Extra 5% off", às vezes com teto "... up to BRL 10.00"
        m = re.search(r"([\d.,]+)\s*%", desc)
        if m:
            pct = _parse_price(m.group(1))
            if 0 < pct < 100:
                discount = round(price * pct / 100, 2)
                cap = re.search(r"up to\s+[A-Za-z]{0,3}\s*([\d.,]+)", desc, re.IGNORECASE)
                if cap:
                    discount = min(discount, _parse_price(cap.group(1)))
    else:
        # fixo: "... get BRL 28.19 off" / "BRL 28.19 off" / "R$ 28,19 de desconto"
        for pat in (r"get\s+[A-Za-z]{0,3}\s*([\d.,]+)\s*off",
                    r"(?:[A-Z]{3}|R\$)\s*([\d.,]+)\s*(?:off|de desconto)"):
            m = re.search(pat, desc, re.IGNORECASE)
            if m:
                discount = _parse_price(m.group(1))
                break
    applicable = discount > 0 and price >= min_spend
    return {
        "code": code,
        "discount": discount,
        "min_spend": min_spend,
        "fixed": "%" not in desc,  # só cupons de valor fixo valem para outros produtos
        "applicable": applicable,
        "final_price": round(price - discount, 2) if applicable else price,
    }


def parse_product(raw: dict) -> dict | None:
    """Normaliza um produto da API para o formato interno."""
    try:
        product_id = str(raw["product_id"])
        title = raw.get("product_title", "")
        price_str = raw.get("target_sale_price") or raw.get("sale_price") or "0"
        web_price = _parse_price(price_str)
        # preço no app costuma ser o do checkout (~10% menor; o link de afiliado
        # abre o app) — usa o menor dos dois e guarda o do site para exibição
        app_str = raw.get("target_app_sale_price") or raw.get("app_sale_price")
        app_price = _parse_price(app_str) if app_str else 0.0
        price = app_price if 0 < app_price < web_price else web_price
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
            "has_affiliate": bool(raw.get("promotion_link")),
            "sku_id": str(raw.get("sku_id", "")),
            "title": title,
            "price": price,
            "web_price": web_price,
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
