"""
Testes locais - roda sem precisar de credenciais do AliExpress.
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))


def test_database():
    print("\n--- Teste: database ---")
    import database
    from database import init_db, upsert_product, can_post, mark_posted

    database.DB_PATH = "test_promo_bot.db"
    if os.path.exists("test_promo_bot.db"):
        os.remove("test_promo_bot.db")
    init_db()

    # produto novo
    state = upsert_product("PROD001", "Teclado Mecânico RGB", 299.90)
    assert state["is_new"] is True
    assert state["min_price"] == 299.90
    print(f"  ✅ Produto novo inserido. min_price={state['min_price']}")

    # mesmo produto, preço menor
    state2 = upsert_product("PROD001", "Teclado Mecânico RGB", 249.90)
    assert state2["is_new"] is False
    assert state2["min_price"] == 299.90, "min_price deve ser o valor antes desta atualização"
    print(f"  ✅ Atualização OK. min_price histórico={state2['min_price']}, preço atual=249.90")

    # pode postar: nunca postado
    assert can_post("PROD001") is True
    print("  ✅ can_post → True (nunca postado)")

    # após postar, não pode repostar imediatamente
    mark_posted("PROD001")
    assert can_post("PROD001") is False
    print("  ✅ can_post → False (recém postado)")

    # calcula queda de preço corretamente
    drop_pct = (state2["min_price"] - 249.90) / state2["min_price"] * 100
    assert abs(drop_pct - 16.67) < 0.1, f"Expected ~16.67%, got {drop_pct:.2f}%"
    print(f"  ✅ Cálculo de queda: -{drop_pct:.2f}% (esperado ~16.67%)")

    try:
        import gc; gc.collect()
        os.remove("test_promo_bot.db")
    except PermissionError:
        pass
    print("  ✅ Database OK")


def test_price_parser():
    print("\n--- Teste: aliexpress._parse_price ---")
    from aliexpress import _parse_price

    cases = [
        ("99.90",       99.90),
        ("99.90 BRL",   99.90),
        ("1,299.90",    1299.90),  # formato US com milhar
        ("1.299,90",    1299.90),  # formato BR com milhar
        ("0",           0.0),
        ("R$ 89.90",    89.90),    # caso improvável mas defensivo
    ]
    for raw, expected in cases:
        result = _parse_price(raw)
        assert abs(result - expected) < 0.01, f"_parse_price({raw!r}) = {result}, esperado {expected}"
        print(f"  ✅ _parse_price({raw!r}) = {result}")


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
    assert abs(product["price"] - 89.90) < 0.01
    assert abs(product["original_price"] - 149.90) < 0.01
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
        "title": "Mouse Gamer RGB 7200 DPI Wireless com cabo trançado e sensor óptico de alta precisão",
        "price": 89.90,
        "original_price": 1499.90,  # milhar → testa formatação BR
        "rating": 4.6,
        "sales": 15230,
        "link": "https://s.click.aliexpress.com/e/abc123",
        "image_url": "https://ae01.alicdn.com/kf/example.jpg",
    }
    msg = _format_message(product, 40.1)

    # preço em BRL correto
    assert "89,90" in msg, "Preço atual deve estar formatado em BRL"
    assert "1.499,90" in msg, "Preço original deve estar formatado em BRL com milhar"
    # desconto
    assert "-40%" in msg
    # strikethrough HTML correto (não markdown)
    assert "<s>" in msg, "Deve usar <s> para strikethrough (HTML mode), não ~~"
    assert "~~" not in msg, "Não deve usar ~~ (markdown) em HTML mode"
    # link afiliado
    assert 'href="https://s.click.aliexpress.com/e/abc123"' in msg
    # título truncado se necessário
    assert len(msg) < 1024, "Mensagem deve caber no limite de caption do Telegram"

    print("  ✅ Strikethrough HTML: <s> ✓")
    print("  ✅ Preço BR formatado: 89,90 e 1.499,90 ✓")
    print("  ✅ Desconto: -40% ✓")
    print("  ✅ Tamanho: {} chars ✓".format(len(msg)))
    print("\n  Preview (sem tags HTML):")
    import re
    clean = re.sub(r"<[^>]+>", "", msg)
    for line in clean.split("\n"):
        print(f"     {line}")


def test_cold_start_logic():
    print("\n--- Teste: cold start logic ---")
    # simula o fluxo do monitor para produto novo com desconto alto
    import database
    from database import init_db, upsert_product, can_post

    database.DB_PATH = "test_cold.db"
    if os.path.exists("test_cold.db"):
        os.remove("test_cold.db")
    init_db()

    product = {
        "product_id": "COLD001",
        "title": "Produto novo com desconto alto",
        "price": 50.0,
        "original_price": 100.0,
        "discount_pct": 50.0,
        "link": "https://s.click.aliexpress.com/e/test",
        "image_url": "",
        "rating": 4.0,
        "sales": 500,
    }

    state = upsert_product(product["product_id"], product["title"], product["price"])
    assert state["is_new"] is True

    # lógica do monitor: cold start com desconto >= 30% → deve postar
    from monitor import COLD_START_DISCOUNT_THRESHOLD
    should_post = state["is_new"] and product["discount_pct"] >= COLD_START_DISCOUNT_THRESHOLD and can_post(product["product_id"])
    assert should_post is True
    print(f"  ✅ Cold start com {product['discount_pct']}% desconto → posta ✓")

    # produto novo com desconto baixo → NÃO deve postar
    product2 = {**product, "product_id": "COLD002", "discount_pct": 10.0}
    state2 = upsert_product(product2["product_id"], product2["title"], product2["price"])
    should_post2 = state2["is_new"] and product2["discount_pct"] >= COLD_START_DISCOUNT_THRESHOLD
    assert should_post2 is False
    print(f"  ✅ Cold start com {product2['discount_pct']}% desconto → não posta ✓")

    try:
        import gc; gc.collect()
        os.remove("test_cold.db")
    except PermissionError:
        pass
    print("  ✅ Cold start logic OK")


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

    if not TELEGRAM_CHANNEL_ID or TELEGRAM_CHANNEL_ID == "PREENCHER_DEPOIS":
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
    test_price_parser()
    test_aliexpress_parser()
    test_telegram_message_format()
    test_cold_start_logic()
    test_telegram_connection()
    print("\n✅ Todos os testes passaram!\n")
