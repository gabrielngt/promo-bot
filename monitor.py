from config import CATEGORIES, PRODUCTS_PER_CATEGORY
from aliexpress import get_hot_products, get_products_by_brand, parse_product
from database import upsert_product, can_post, mark_posted, get_settings
from telegram_bot import post_product

import re
import time


def _is_peripheral(title: str, keywords: list[str]) -> bool:
    t = title.lower()
    return any(kw.lower() in t for kw in keywords)


def _matches_brand(title: str, brands: list) -> bool:
    if not brands:
        return True
    t = title.lower()
    return any(entry["name"].lower() in t for entry in brands)


def _title_fingerprint(title: str) -> str:
    words = sorted(re.findall(r'[a-z0-9]{3,}', title.lower()))
    return "".join(words)[:60]


def check_category(category_id: str, settings: dict, posts_so_far: int = 0, raw_products_override: list = None, seen_fingerprints: dict = None) -> int:
    if seen_fingerprints is None:
        seen_fingerprints = {}

    raw_list = raw_products_override if raw_products_override is not None else get_hot_products(category_id, page_size=PRODUCTS_PER_CATEGORY)

    # Dedup por título similar — mantém o mais barato por fingerprint neste lote
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
    seen_fingerprints.update({fp: True for fp in cheapest})

    posts_made = 0
    max_posts = settings["max_posts_per_cycle"] - posts_so_far
    keywords = settings["peripheral_keywords"]
    brands = settings["brand_whitelist"]
    threshold = settings["price_drop_threshold"] * 100
    cold_threshold = settings["cold_start_threshold"] * 100

    for product in cheapest.values():
        if posts_made >= max_posts:
            break

        if keywords and not _is_peripheral(product["title"], keywords):
            continue

        if not _matches_brand(product["title"], brands):
            continue

        state = upsert_product(product["product_id"], product["title"], product["price"], product.get("link", ""))

        if state["is_new"]:
            if product["discount_pct"] >= cold_threshold and can_post(product["product_id"], product["price"]):
                print(f"[Monitor] Cold start deal: {product['title'][:50]} | -{product['discount_pct']:.0f}% | R$ {product['price']:.2f}")
                success = post_product(product, product["discount_pct"])
                if success:
                    mark_posted(product["product_id"], product["price"])
                    posts_made += 1
                    time.sleep(2)
            continue

        min_price = state["min_price"]
        if min_price <= 0:
            continue

        drop_pct = (min_price - product["price"]) / min_price * 100

        if drop_pct >= threshold and can_post(product["product_id"], product["price"]):
            print(f"[Monitor] Promoção detectada: {product['title'][:50]} | -{drop_pct:.1f}% | R$ {product['price']:.2f}")
            success = post_product(product, drop_pct)
            if success:
                mark_posted(product["product_id"], product["price"])
                posts_made += 1
                time.sleep(2)

    return posts_made


def run_check():
    settings = get_settings()
    brands = settings["brand_whitelist"]
    max_posts = settings["max_posts_per_cycle"]
    total_posts = 0
    seen_fingerprints: dict = {}  # compartilhado entre categorias e marcas no ciclo

    # busca por categoria (sempre)
    print(f"[Monitor] Verificando {len(CATEGORIES)} categorias...")
    for category_id in CATEGORIES:
        if total_posts >= max_posts:
            break
        posts = check_category(category_id, settings, posts_so_far=total_posts, seen_fingerprints=seen_fingerprints)
        total_posts += posts
        time.sleep(1)

    # busca por marca — cada marca tem orçamento próprio
    if brands:
        print(f"[Monitor] Buscando {len(brands)} marca(s) na whitelist...")
        per_brand_max = max(2, max_posts // len(brands))
        brand_settings = {**settings, "max_posts_per_cycle": per_brand_max}
        for entry in brands:
            brand_name = entry["name"]
            kw_filter = entry["keywords"]  # tipos de produto para esta marca
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

    print(f"[Monitor] Verificação concluída. {total_posts} promoções postadas.")
    return total_posts
