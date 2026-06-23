from config import CATEGORIES, PRODUCTS_PER_CATEGORY
from aliexpress import get_hot_products, parse_product
from database import upsert_product, can_post, mark_posted, get_settings
from telegram_bot import post_product

import time


def _is_peripheral(title: str, keywords: list[str]) -> bool:
    t = title.lower()
    return any(kw.lower() in t for kw in keywords)


def _matches_brand(title: str, brands: list[str]) -> bool:
    if not brands:
        return True
    t = title.lower()
    return any(brand.lower() in t for brand in brands)


def check_category(category_id: str, settings: dict) -> int:
    raw_products = get_hot_products(category_id, page_size=PRODUCTS_PER_CATEGORY)
    posts_made = 0
    keywords = settings["peripheral_keywords"]
    brands = settings["brand_whitelist"]
    threshold = settings["price_drop_threshold"] * 100
    cold_threshold = settings["cold_start_threshold"] * 100

    for raw in raw_products:
        product = parse_product(raw)
        if not product:
            continue

        if keywords and not _is_peripheral(product["title"], keywords):
            continue

        if not _matches_brand(product["title"], brands):
            continue

        state = upsert_product(product["product_id"], product["title"], product["price"], product.get("link", ""))

        if state["is_new"]:
            if product["discount_pct"] >= cold_threshold and can_post(product["product_id"], product["price"]):
                print(
                    f"[Monitor] Cold start deal: {product['title'][:50]} "
                    f"| -{product['discount_pct']:.0f}% | R$ {product['price']:.2f}"
                )
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
            print(
                f"[Monitor] Promoção detectada: {product['title'][:50]} "
                f"| -{drop_pct:.1f}% | R$ {product['price']:.2f}"
            )
            success = post_product(product, drop_pct)
            if success:
                mark_posted(product["product_id"], product["price"])
                posts_made += 1
                time.sleep(2)

    return posts_made


def run_check():
    settings = get_settings()
    print(f"[Monitor] Iniciando verificação de {len(CATEGORIES)} categorias...")
    total_posts = 0
    for category_id in CATEGORIES:
        print(f"[Monitor] Verificando categoria {category_id}...")
        posts = check_category(category_id, settings)
        total_posts += posts
        time.sleep(1)
    print(f"[Monitor] Verificação concluída. {total_posts} promoções postadas.")
    return total_posts
