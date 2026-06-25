from config import CATEGORIES, PRODUCTS_PER_CATEGORY
from aliexpress import get_hot_products, get_products_by_brand, parse_product, get_shipping
from database import upsert_product, can_post, mark_posted, get_settings
from telegram_bot import post_product

import re
import time


def _post_with_shipping(product: dict, pct: float) -> bool:
    """Enriquece com frete (só agora, na hora de postar) e posta."""
    shipping = get_shipping(product["product_id"], product.get("sku_id", ""), product["price"])
    if shipping:
        product["shipping"] = shipping
    return post_product(product, pct)

# Cold start: produto novo (sem histórico próprio) só é postado com base no
# desconto reportado pela API — campo notoriamente inflado. Por isso exigimos
# também sinais de qualidade (avaliação + vendas) antes de postar.
COLD_START_MIN_RATING = 4.0   # 0 a 5
COLD_START_MIN_SALES = 50     # volume recente


def _is_peripheral(title: str, keywords: list[str]) -> bool:
    t = title.lower()
    return any(kw.lower() in t for kw in keywords)


def _is_blacklisted(title: str, blacklist: list[str]) -> bool:
    t = title.lower()
    return any(kw.lower() in t for kw in blacklist)


def _matches_brand(title: str, brands: list) -> bool:
    if not brands:
        return True
    t = title.lower()
    return any(entry["name"].lower() in t for entry in brands)


def _passes_quality(product: dict) -> bool:
    return product["rating"] >= COLD_START_MIN_RATING and product["sales"] >= COLD_START_MIN_SALES


def _title_fingerprint(title: str) -> str:
    words = sorted(re.findall(r'[a-z0-9]{3,}', title.lower()))
    return "".join(words)[:60]


def check_category(category_id: str, settings: dict, posts_so_far: int = 0, raw_products_override: list = None, seen_fingerprints: dict = None) -> int:
    if seen_fingerprints is None:
        seen_fingerprints = {}

    raw_list = raw_products_override if raw_products_override is not None else get_hot_products(category_id, page_size=PRODUCTS_PER_CATEGORY)

    # Dedup local: mantém o mais barato por fingerprint neste lote.
    # Pula fingerprints que JÁ foram postados neste ciclo.
    cheapest: dict[str, dict] = {}
    for raw in raw_list:
        p = parse_product(raw)
        if not p:
            continue
        fp = _title_fingerprint(p["title"])
        if fp in seen_fingerprints:
            continue
        if fp not in cheapest or p["price"] < cheapest[fp]["price"]:
            cheapest[fp] = p

    posts_made = 0
    max_posts = settings["max_posts_per_cycle"] - posts_so_far
    keywords = settings["peripheral_keywords"]
    blacklist = settings["keyword_blacklist"]
    brands = settings["brand_whitelist"]
    threshold = settings["price_drop_threshold"] * 100
    cold_threshold = settings["cold_start_threshold"] * 100

    for fp, product in cheapest.items():
        if posts_made >= max_posts:
            break

        if blacklist and _is_blacklisted(product["title"], blacklist):
            continue

        if keywords and not _is_peripheral(product["title"], keywords):
            continue

        if not _matches_brand(product["title"], brands):
            continue

        state = upsert_product(product["product_id"], product["title"], product["price"], product.get("link", ""))

        if state["is_new"]:
            if (product["discount_pct"] >= cold_threshold
                    and _passes_quality(product)
                    and can_post(product["product_id"], product["price"])):
                print(f"[Monitor] Cold start deal: {product['title'][:50]} | -{product['discount_pct']:.0f}% | R$ {product['price']:.2f}")
                if _post_with_shipping(product, product["discount_pct"]):
                    mark_posted(product["product_id"], product["price"])
                    seen_fingerprints[fp] = True  # marca só o que foi postado
                    posts_made += 1
                    time.sleep(2)
            continue

        min_price = state["min_price"]
        if min_price <= 0:
            continue

        drop_pct = (min_price - product["price"]) / min_price * 100

        if drop_pct >= threshold and can_post(product["product_id"], product["price"]):
            print(f"[Monitor] Promoção detectada: {product['title'][:50]} | -{drop_pct:.1f}% | R$ {product['price']:.2f}")
            if _post_with_shipping(product, drop_pct):
                mark_posted(product["product_id"], product["price"])
                seen_fingerprints[fp] = True  # marca só o que foi postado
                posts_made += 1
                time.sleep(2)

    return posts_made


def run_check():
    settings = get_settings()
    brands = settings["brand_whitelist"]
    max_posts = settings["max_posts_per_cycle"]
    total_posts = 0
    seen_fingerprints: dict = {}  # só fingerprints já POSTADOS neste ciclo

    # Marcas têm prioridade (curadas pelo usuário) e orçamento próprio,
    # mas o total do ciclo nunca passa de max_posts.
    if brands:
        print(f"[Monitor] Buscando {len(brands)} marca(s) na whitelist...")
        per_brand_max = max(1, max_posts // len(brands))
        for entry in brands:
            if total_posts >= max_posts:
                break
            brand_name = entry["name"]
            kw_filter = entry["keywords"]  # tipos de produto para esta marca
            brand_budget = min(per_brand_max, max_posts - total_posts)
            brand_settings = {**settings, "max_posts_per_cycle": brand_budget}
            raw_products = get_products_by_brand(brand_name)
            if kw_filter:
                raw_products = [
                    r for r in raw_products
                    if any(kw.lower() in r.get("product_title", "").lower() for kw in kw_filter)
                ]
            if raw_products:
                posts = check_category(
                    category_id=f"brand:{brand_name}",
                    settings=brand_settings,
                    posts_so_far=0,
                    raw_products_override=raw_products,
                    seen_fingerprints=seen_fingerprints,
                )
                total_posts += posts
            time.sleep(1)

    # Categorias preenchem o orçamento restante até max_posts.
    print(f"[Monitor] Verificando {len(CATEGORIES)} categorias...")
    for category_id in CATEGORIES:
        if total_posts >= max_posts:
            break
        posts = check_category(category_id, settings, posts_so_far=total_posts, seen_fingerprints=seen_fingerprints)
        total_posts += posts
        time.sleep(1)

    print(f"[Monitor] Verificação concluída. {total_posts} promoções postadas.")
    return total_posts
