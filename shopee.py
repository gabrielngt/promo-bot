"""Cliente da Open API de afiliados da Shopee (GraphQL).

Diferenças em relação ao aliexpress.py, todas confirmadas contra a API real:
  - autenticação por assinatura SHA256 no header Authorization;
  - `offerLink` já vem como link de afiliado rastreável — não precisa de uma
    segunda chamada para gerar link (a AliExpress precisa);
  - `commissionRate` é FRAÇÃO (0.43 = 43%), e `commission` já vem em reais;
  - vendedor nacional: preço da API é o final (sem imposto de importação,
    sem ICMS por dentro, sem cálculo de frete internacional).
"""
import hashlib
import json
import time
import requests

from config import SHOPEE_APP_ID, SHOPEE_SECRET

API_URL = "https://open-api.affiliate.shopee.com.br/graphql"


def _post(query: str, variables: dict | None = None) -> dict | None:
    """Assina e envia uma query GraphQL. A assinatura cobre o corpo exato, então
    o payload enviado tem que ser a MESMA string usada no hash."""
    payload = json.dumps({"query": query, "variables": variables or {}}, separators=(",", ":"))
    ts = int(time.time())
    signature = hashlib.sha256(f"{SHOPEE_APP_ID}{ts}{payload}{SHOPEE_SECRET}".encode()).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={ts}, Signature={signature}",
    }
    try:
        resp = requests.post(API_URL, data=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors"):
            print(f"[Shopee] GraphQL error: {json.dumps(data['errors'])[:300]}")
            return None
        return data.get("data")
    except Exception as e:
        print(f"[Shopee] Exceção na chamada: {e}")
        return None


def _f(value, default: float = 0.0) -> float:
    """Números vêm como string ('49.9'); converte sem quebrar em nulo/vazio."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


_PRODUCT_FIELDS = """
    itemId productName priceMin priceMax priceDiscountRate
    commissionRate commission sales ratingStar
    imageUrl offerLink productLink shopName
"""


# Ordenação do productOfferV2 (descoberto por sondagem — o enum não é exposto
# na introspection): 2 = volume de vendas desc. É o equivalente ao
# LAST_VOLUME_DESC da AliExpress e o único que devolve itens com histórico real;
# o default traz muito anúncio novo com 0 vendas.
SORT_BY_SALES = 2


def search_products(keyword: str, limit: int = 20, page: int = 1) -> list[dict]:
    """productOfferV2 — produtos no programa de afiliados que casam com a keyword."""
    query = """
    query($keyword: String!, $limit: Int!, $page: Int!, $sortType: Int!) {
      productOfferV2(keyword: $keyword, limit: $limit, page: $page, sortType: $sortType) {
        nodes { %s }
        pageInfo { page limit hasNextPage }
      }
    }
    """ % _PRODUCT_FIELDS
    data = _post(query, {"keyword": keyword, "limit": limit, "page": page,
                         "sortType": SORT_BY_SALES})
    if not data:
        return []
    return data.get("productOfferV2", {}).get("nodes", []) or []


def generate_short_link(url: str, sub_ids: list[str] | None = None) -> str | None:
    """generateShortLink — para URLs avulsas (produto que não veio do productOfferV2,
    que já traz offerLink pronto). subIds viram etiquetas no relatório de conversão."""
    query = """
    mutation($input: GenerateShortLinkInput!) {
      generateShortLink(input: $input) { shortLink }
    }
    """
    payload = {"originUrl": url, "subIds": sub_ids or ["telegram"]}
    data = _post(query, {"input": payload})
    if not data:
        return None
    return (data.get("generateShortLink") or {}).get("shortLink")


def parse_product(raw: dict) -> dict | None:
    """Normaliza para o mesmo formato do aliexpress.parse_product, para o monitor
    tratar as duas lojas igual."""
    try:
        price = _f(raw.get("priceMin"))
        if price <= 0:
            return None
        # priceDiscountRate é percentual inteiro (38 = 38%); reconstrói o "de"
        discount_pct = _f(raw.get("priceDiscountRate"))
        original = round(price / (1 - discount_pct / 100), 2) if 0 < discount_pct < 100 else price
        link = raw.get("offerLink") or raw.get("productLink") or ""
        return {
            "store": "shopee",
            "product_id": str(raw["itemId"]),
            "has_affiliate": bool(raw.get("offerLink")),
            "sku_id": "",
            "title": raw.get("productName", ""),
            "price": price,
            "web_price": price,          # Shopee não tem preço de app diferente
            "original_price": original,
            "discount_pct": discount_pct,
            "coupon": None,              # cupom não vem no productOfferV2
            "link": link,
            "image_url": raw.get("imageUrl", ""),
            "rating": _f(raw.get("ratingStar")),
            "sales": int(_f(raw.get("sales"))),
            # commissionRate é fração (0.43 = 43%); guardamos em % para exibir
            "commission_pct": round(_f(raw.get("commissionRate")) * 100, 2),
            "commission_brl": _f(raw.get("commission")),
            "shop_name": raw.get("shopName", ""),
        }
    except Exception as e:
        print(f"[Shopee] Erro ao parsear produto {raw.get('itemId')}: {e}")
        return None
