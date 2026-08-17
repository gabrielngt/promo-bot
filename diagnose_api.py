"""
Sonda da API de afiliados — somente leitura, NÃO posta e NÃO grava nada.

Despeja os campos crus que a API retorna para responder quatro perguntas:
  1. Quais campos de preço existem e qual bate com o checkout
     (target_sale_price vs target_app_sale_price; efeito do ship_to_country)?
  2. Em que formato/idioma vem o promo_code_info.code_value dos cupons?
  3. Quais campanhas o featuredpromo.get lista e como vêm os produtos?
  4. order.listbyindex: start_time/end_time aceitam 'yyyy-MM-dd HH:mm:ss'?
     Qual é o campo de paginação de verdade na resposta? (sales.py assume um
     formato não confirmado pela documentação — ver aliexpress.get_affiliate_orders)

O app tem whitelist de IP na AliExpress, então rode ONDE O BOT RODA
(console SSH/Kudu do Azure App Service):

    python diagnose_api.py [keyword]
"""
import json
import sys
from dotenv import load_dotenv

load_dotenv()
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import requests
from aliexpress import _base_params, _sign, _extract_products, API_URL
from config import ALIEXPRESS_TRACKING_ID

PRICE_FIELDS = [
    "sale_price", "app_sale_price", "original_price",
    "target_sale_price", "target_app_sale_price", "target_original_price",
    "sale_price_currency", "target_sale_price_currency", "discount",
]


def call(method: str, extra: dict) -> dict:
    params = _base_params(method)
    params.update(extra)
    params["sign"] = _sign(params)
    resp = requests.post(API_URL, data=params, timeout=20)
    return resp.json()


def query_products(keyword: str, ship_to: str | None) -> list:
    extra = {
        "tracking_id": ALIEXPRESS_TRACKING_ID,
        "keywords": keyword,
        "page_no": "1",
        "page_size": "3",
        "target_currency": "BRL",
        "target_language": "PT",
    }
    if ship_to:
        extra["ship_to_country"] = ship_to
    data = call("aliexpress.affiliate.product.query", extra)
    if "error_response" in data:
        print(f"   ❌ erro: {data['error_response']}")
        return []
    result = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})
    if result.get("resp_code") != 200:
        print(f"   ❌ resp_code {result.get('resp_code')}: {result.get('resp_msg')}")
        return []
    return _extract_products(result)


def show_prices(p: dict):
    print(f"   #{p.get('product_id')}  {str(p.get('product_title'))[:60]}")
    for f in PRICE_FIELDS:
        if p.get(f) not in (None, ""):
            print(f"      {f:35} = {p[f]}")


def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else "mouse gamer"

    # ── 1. Campos de preço: com vs sem ship_to_country ──
    print(f"\n══ 1. product.query '{keyword}' SEM ship_to_country ══")
    base = query_products(keyword, ship_to=None)
    for p in base:
        show_prices(p)

    print(f"\n══ 1b. product.query '{keyword}' COM ship_to_country=BR ══")
    br = query_products(keyword, ship_to="BR")
    for p in br:
        show_prices(p)

    ids_base = {str(p.get("product_id")): p for p in base}
    for p in br:
        pid = str(p.get("product_id"))
        if pid in ids_base and ids_base[pid].get("target_sale_price") != p.get("target_sale_price"):
            print(f"\n   ⚠️  PREÇO MUDOU com ship_to_country: #{pid} "
                  f"{ids_base[pid].get('target_sale_price')} → {p.get('target_sale_price')}")

    # ── 2. Cupons: formato real do promo_code_info ──
    print("\n══ 2. promo_code_info encontrados (formato cru do code_value) ══")
    found = 0
    for p in base + br:
        info = p.get("promo_code_info")
        if info:
            found += 1
            print(json.dumps(info, indent=2, ensure_ascii=False))
    if not found:
        print("   (nenhum produto da amostra tem cupom — tente outra keyword)")

    # ── 3. Campanhas em destaque ──
    print("\n══ 3. featuredpromo.get — campanhas ativas ══")
    data = call("aliexpress.affiliate.featuredpromo.get", {"tracking_id": ALIEXPRESS_TRACKING_ID})
    if "error_response" in data:
        print(f"   ❌ erro: {data['error_response']}")
        return
    result = data.get("aliexpress_affiliate_featuredpromo_get_response", {}).get("resp_result", {})
    print(f"   resp_code: {result.get('resp_code')} {result.get('resp_msg') or ''}")
    promos = result.get("result", {}).get("promos", [])
    if isinstance(promos, dict):
        promos = promos.get("promo", [])
    for promo in promos or []:
        print(f"   • {json.dumps(promo, ensure_ascii=False)}")

    if promos:
        name = promos[0].get("promo_name")
        print(f"\n══ 3b. featuredpromo.products.get '{name}' (amostra) ══")
        data = call("aliexpress.affiliate.featuredpromo.products.get", {
            "promotion_name": name,
            "tracking_id": ALIEXPRESS_TRACKING_ID,
            "page_no": "1",
            "page_size": "3",
            "target_currency": "BRL",
            "target_language": "PT",
            "country": "BR",
        })
        if "error_response" in data:
            print(f"   ❌ erro: {data['error_response']}")
            return
        result = data.get("aliexpress_affiliate_featuredpromo_products_get_response", {}).get("resp_result", {})
        print(f"   resp_code: {result.get('resp_code')} {result.get('resp_msg') or ''}")
        for p in _extract_products(result):
            show_prices(p)

    # ── 4. Pedidos de afiliado: formato de data e paginação ──
    print("\n══ 4. order.listbyindex — formato de data e paginação (não confirmados) ══")
    from datetime import datetime, timedelta, timezone
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=60)
    data = call("aliexpress.affiliate.order.listbyindex", {
        "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Payment Completed",
        "page_size": "5",
    })
    if "error_response" in data:
        print(f"   ❌ erro: {data['error_response']}")
        print("   Se a mensagem reclamar do formato de start_time/end_time, ajuste")
        print("   o strftime em sales.py e em aliexpress.get_affiliate_orders.")
    else:
        result = data.get("aliexpress_affiliate_order_listbyindex_response", {}).get("resp_result", {})
        print(f"   resp_code: {result.get('resp_code')} {result.get('resp_msg') or ''}")
        r = result.get("result", {})
        print("   Campos de nível 'result' (procure aqui o cursor de paginação):")
        for k, v in r.items():
            if k != "orders":
                print(f"      {k} = {v}")
        orders = r.get("orders", [])
        if isinstance(orders, dict):
            orders = orders.get("order", [])
        if orders:
            print(f"   Primeiro pedido cru (confira created_time e nomes dos campos de valor):")
            print(json.dumps(orders[0], indent=2, ensure_ascii=False))
        else:
            print("   (nenhum pedido 'Payment Completed' nos últimos 60 dias — normal se ainda não vendeu)")

    print("\nPronto. Compare os preços acima com a página do produto no site/app")
    print("para ver qual campo bate com o checkout (e se o imposto está incluso).")


if __name__ == "__main__":
    main()
