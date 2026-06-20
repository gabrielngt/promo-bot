from config import CATEGORIES, PRODUCTS_PER_CATEGORY, PRICE_DROP_THRESHOLD
from aliexpress import get_hot_products, parse_product
from database import upsert_product, can_post, mark_posted
from telegram_bot import post_product

import time


def check_category(category_id: str) -> int:
    """Checks one category and posts deals. Returns number of posts made."""
    raw_products = get_hot_products(category_id, page_size=PRODUCTS_PER_CATEGORY)
    posts_made = 0

    for raw in raw_products:
        product = parse_product(raw)
        if not product:
            continue

        state = upsert_product(product["product_id"], product["title"], product["price"])

        if state["is_new"]:
            # produto novo: só salva, aguarda histórico para comparar
            continue

        min_price = state["min_price"]
        if min_price <= 0:
            continue

        drop_pct = (min_price - product["price"]) / min_price * 100

        if drop_pct >= PRICE_DROP_THRESHOLD * 100:
            if can_post(product["product_id"]):
                print(
                    f"[Monitor] Promoção detectada: {product['title'][:50]} "
                    f"| -{drop_pct:.1f}% | R$ {product['price']:.2f}"
                )
                success = post_product(product, drop_pct)
                if success:
                    mark_posted(product["product_id"])
                    posts_made += 1
                    time.sleep(2)  # evita flood no Telegram

    return posts_made


def run_check():
    """Runs a full check across all configured categories."""
    print(f"[Monitor] Iniciando verificação de {len(CATEGORIES)} categorias...")
    total_posts = 0
    for category_id in CATEGORIES:
        print(f"[Monitor] Verificando categoria {category_id}...")
        posts = check_category(category_id)
        total_posts += posts
        time.sleep(1)  # respeita rate limit da API
    print(f"[Monitor] Verificação concluída. {total_posts} promoções postadas.")
    return total_posts
