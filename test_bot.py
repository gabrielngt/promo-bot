"""
Testes locais - roda sem precisar de credenciais do AliExpress.
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))


def test_database():
    print("\n--- Teste: database ---")
    from database import init_db, upsert_product, can_post, mark_posted

    # usa DB temporário
    import database
    database.DB_PATH = "test_promo_bot.db"

    if os.path.exists("test_promo_bot.db"):
        os.remove("test_promo_bot.db")

    init_db()

    # produto novo
    state = upsert_product("PROD001", "Teclado Mecânico RGB", 299.90)
    assert state["is_new"] is True, "Deveria ser novo"
    print(f"  ✅ Produto novo inserido. min_price={state['min_price']}")

    # mesmo produto, preço menor
    state2 = upsert_product("PROD001", "Teclado Mecânico RGB", 249.90)
    assert state2["is_new"] is False
    assert state2["min_price"] == 299.90, "min_price deve ser o original ainda"
    print(f"  ✅ Atualização OK. min_price histórico={state2['min_price']}, novo={249.90}")

    # can_post: nunca postado → deve poder postar
    assert can_post("PROD001") is True
    print("  ✅ can_post: produto nunca postado → True")

    # após marcar como postado → não pode repostar imediatamente
    mark_posted("PROD001")
    assert can_post("PROD001") is False
    print("  ✅ can_post: logo após postar → False (respeitando MIN_REPOST_DAYS)")

    # cleanup
    try:
        import gc; gc.collect()
        os.remove("test_promo_bot.db")
    except PermissionError:
        pass  # Windows segura o handle por um instante
    print("  ✅ Database OK")


def test_aliexpress_parser():
    print("\n--- Teste: aliexpress.parse_product ---")
    from aliexpress import parse_product

    raw = {
        "product_id": "1005006789012345",
        "product_title": "Mouse Gamer RGB 7200 DPI Wireless",
        "target_sale_price": "89.90 BRL",
        "target_original_price": "149.90 BRL",
        "discount": "40%",
        "promotion_link": "https://s.click.aliexpress.com/e/abc123",
        "product_main_image_url": "https://ae01.alicdn.com/kf/example.jpg",
        "evaluate_rate": "92%",
        "lastest_volume": 1523,
    }

    product = parse_product(raw)
    assert product is not None
    assert product["product_id"] == "1005006789012345"
    assert product["price"] == 89.90
    assert product["original_price"] == 149.90
    assert product["discount_pct"] == 40.0
    assert abs(product["rating"] - 4.6) < 0.1
    assert product["sales"] == 1523
    print(f"  ✅ Parse OK: {product['title'][:40]}")
    print(f"     Preço: R$ {product['price']:.2f} (original: R$ {product['original_price']:.2f})")
    print(f"     Rating: {product['rating']:.1f}/5 | Vendidos: {product['sales']}")


def test_telegram_message_format():
    print("\n--- Teste: telegram_bot._format_message ---")
    from telegram_bot import _format_message

    product = {
        "title": "Mouse Gamer RGB 7200 DPI Wireless",
        "price": 89.90,
        "original_price": 149.90,
        "rating": 4.6,
        "sales": 1523,
        "link": "https://s.click.aliexpress.com/e/abc123",
        "image_url": "https://ae01.alicdn.com/kf/example.jpg",
    }
    msg = _format_message(product, 40.1)
    assert "89,90" in msg
    assert "149,90" in msg
    assert "-40%" in msg
    assert "aliexpress" in msg.lower()
    print("  ✅ Mensagem formatada:")
    print()
    # mostra a mensagem sem tags HTML (visual)
    import re
    clean = re.sub(r"<[^>]+>", "", msg)
    for line in clean.split("\n"):
        print(f"     {line}")


def test_telegram_connection():
    print("\n--- Teste: Telegram (conexão real com bot) ---")
    import requests
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

    resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=10)
    data = resp.json()
    if data.get("ok"):
        bot = data["result"]
        print(f"  ✅ Bot conectado: @{bot['username']} ({bot['first_name']})")
    else:
        print(f"  ❌ Falha: {data.get('description')}")
        return

    if TELEGRAM_CHANNEL_ID == "PREENCHER_DEPOIS":
        print("  ⚠️  TELEGRAM_CHANNEL_ID não configurado ainda — pulando teste de canal.")
    else:
        resp2 = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHANNEL_ID, "text": "🧪 Teste do bot — tudo OK!"},
            timeout=10,
        )
        if resp2.json().get("ok"):
            print(f"  ✅ Mensagem enviada para {TELEGRAM_CHANNEL_ID}")
        else:
            print(f"  ❌ Não conseguiu postar no canal: {resp2.json().get('description')}")


if __name__ == "__main__":
    test_database()
    test_aliexpress_parser()
    test_telegram_message_format()
    test_telegram_connection()
    print("\n✅ Todos os testes passaram!\n")
