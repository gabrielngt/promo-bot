"""
Testes locais - roda sem precisar de credenciais do AliExpress.
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()


def test_database():
    print("\n--- Teste: database ---")
    from database import init_db, upsert_product, can_post, mark_posted, delete_product

    init_db()

    # produto novo
    state = upsert_product("TEST_PROD001", "Teclado Mecânico RGB", 299.90)
    assert state["is_new"] is True
    assert state["min_price"] == 299.90
    print(f"  ✅ Produto novo inserido. min_price={state['min_price']}")

    # mesmo produto, preço menor
    state2 = upsert_product("TEST_PROD001", "Teclado Mecânico RGB", 249.90)
    assert state2["is_new"] is False
    assert state2["min_price"] == 299.90, "min_price deve ser o valor antes desta atualização"
    print(f"  ✅ Atualização OK. min_price histórico={state2['min_price']}, preço atual=249.90")

    # pode postar: nunca postado
    assert can_post("TEST_PROD001") is True
    print("  ✅ can_post → True (nunca postado)")

    # após postar, não pode repostar imediatamente
    mark_posted("TEST_PROD001")
    assert can_post("TEST_PROD001") is False
    print("  ✅ can_post → False (recém postado)")

    # calcula queda de preço corretamente
    drop_pct = (state2["min_price"] - 249.90) / state2["min_price"] * 100
    assert abs(drop_pct - 16.67) < 0.1, f"Expected ~16.67%, got {drop_pct:.2f}%"
    print(f"  ✅ Cálculo de queda: -{drop_pct:.2f}% (esperado ~16.67%)")

    delete_product("TEST_PROD001")
    print("  ✅ Database OK")


def test_price_parser():
    print("\n--- Teste: aliexpress._parse_price ---")
    from aliexpress import _parse_price

    cases = [
        ("99.90",       99.90),
        ("99.90 BRL",   99.90),
        ("1,299.90",    1299.90),  # formato US com milhar
        ("1.299,90",    1299.90),  # formato BR com milhar
        ("1,299",       1299.0),   # milhar US sem decimais
        ("299,90",      299.90),   # decimal BR sem milhar
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

    # com preço de app menor que o do site → usa o do app (é o do checkout)
    raw_app = {**raw, "target_sale_price": "280.52", "target_app_sale_price": "251.99"}
    p2 = parse_product(raw_app)
    assert abs(p2["price"] - 251.99) < 0.01
    assert abs(p2["web_price"] - 280.52) < 0.01
    print(f"  ✅ Preço do app: usa R$ {p2['price']:.2f} (site R$ {p2['web_price']:.2f})")


def test_coupon_parser():
    print("\n--- Teste: aliexpress._parse_coupon ---")
    from aliexpress import _parse_coupon

    def raw(desc, min_spend="0"):
        return {"promo_code_info": {"promo_code": "TESTE", "code_value": desc, "code_mini_spend": min_spend}}

    # fixo em inglês (formato conhecido da API)
    c = _parse_coupon(raw("Spend BRL 141.00, get BRL 28.19 off", "141.00"), 200.0)
    assert c["applicable"] and abs(c["discount"] - 28.19) < 0.01
    assert abs(c["final_price"] - 171.81) < 0.01
    print(f"  ✅ Fixo EN: -R$ {c['discount']:.2f} → R$ {c['final_price']:.2f}")

    # fixo abaixo do gasto mínimo → não aplicável, preço não muda
    c = _parse_coupon(raw("Spend BRL 141.00, get BRL 28.19 off", "141.00"), 100.0)
    assert not c["applicable"] and c["final_price"] == 100.0
    print("  ✅ Fixo abaixo do min_spend: não aplica")

    # percentual simples
    c = _parse_coupon(raw("Extra 5% off"), 200.0)
    assert c["applicable"] and abs(c["discount"] - 10.0) < 0.01
    assert abs(c["final_price"] - 190.0) < 0.01
    print(f"  ✅ Percentual: -R$ {c['discount']:.2f} → R$ {c['final_price']:.2f}")

    # percentual com teto
    c = _parse_coupon(raw("Extra 10% off, up to BRL 15.00"), 300.0)
    assert c["applicable"] and abs(c["discount"] - 15.0) < 0.01
    print(f"  ✅ Percentual com teto: -R$ {c['discount']:.2f} (limitado a 15,00)")

    # fixo em português (defensivo, target_language=PT)
    c = _parse_coupon(raw("R$ 20,00 de desconto"), 100.0)
    assert c["applicable"] and abs(c["discount"] - 20.0) < 0.01
    print(f"  ✅ Fixo PT: -R$ {c['discount']:.2f}")

    # sem código → None
    assert _parse_coupon({}, 100.0) is None
    print("  ✅ Sem cupom: None")


def test_checkout_total():
    print("\n--- Teste: total estimado com impostos ---")
    from telegram_bot import _format_message

    product = {
        "title": "Mouse Teste",
        "price": 100.0,
        "original_price": 100.0,
        "rating": 0,
        "sales": 0,
        "link": "https://s.click.aliexpress.com/e/abc",
        "shipping": {"fee": 20.0, "min_days": 10, "max_days": 15},
        "taxes": {"ii": 0.0, "icms": 0.20},
    }
    msg = _format_message(product, 0)
    # (100 + 20) / (1 - 0.20) = 150.00
    assert "Total estimado no checkout" in msg
    assert "150,00" in msg, f"Esperado 150,00 na mensagem:\n{msg}"
    print("  ✅ ICMS 20% por dentro: (100+20)/0,8 = R$ 150,00")

    # com II de 20%: (100+20) × 1,2 / 0,8 = 180.00
    product["taxes"] = {"ii": 0.20, "icms": 0.20}
    msg = _format_message(product, 0)
    assert "180,00" in msg
    print("  ✅ II 20% + ICMS 20%: R$ 180,00")

    # sem alíquotas configuradas → cai no total simples com frete
    product["taxes"] = {"ii": 0.0, "icms": 0.0}
    msg = _format_message(product, 0)
    assert "Total com frete" in msg and "120,00" in msg
    print("  ✅ Sem impostos: total simples R$ 120,00")


def test_checkout_price_target():
    print("\n--- Teste: monitor._checkout_price (alvo da watchlist) ---")
    from monitor import _checkout_price

    settings = {"import_tax_rate": 0.0, "icms_rate": 0.20}
    p = {"price": 100.0, "coupon": None}
    assert abs(_checkout_price(p, settings) - 125.0) < 0.01  # 100 / 0,8
    print("  ✅ Sem cupom: R$ 100 → final R$ 125,00 (ICMS 20% por dentro)")

    p = {"price": 100.0, "coupon": {"applicable": True, "final_price": 80.0}}
    assert abs(_checkout_price(p, settings) - 100.0) < 0.01  # 80 / 0,8
    print("  ✅ Com cupom aplicável: R$ 80 → final R$ 100,00")

    p = {"price": 100.0, "coupon": {"applicable": False, "final_price": 100.0}}
    assert abs(_checkout_price(p, settings) - 125.0) < 0.01  # cupom não aplicável = ignora
    print("  ✅ Cupom não aplicável: usa o preço-base")

    settings = {"import_tax_rate": 0.20, "icms_rate": 0.20}
    p = {"price": 100.0, "coupon": {"applicable": True, "final_price": 80.0}}
    assert abs(_checkout_price(p, settings) - 120.0) < 0.01  # 80 × 1,2 / 0,8
    print("  ✅ Com II 20%: R$ 80 → final R$ 120,00")


def test_campaign_coupons():
    print("\n--- Teste: cupons de campanha (melhor cupom + checkout do print real) ---")
    from database import _parse_campaign_entry
    from monitor import _apply_best_coupon, _checkout_price

    assert _parse_campaign_entry("BRT28 141 28") == {"code": "BRT28", "min_spend": 141.0, "discount": 28.0}
    assert _parse_campaign_entry("linha invalida") is None
    assert _parse_campaign_entry("BRT28 abc 28") is None
    print("  ✅ Parse de campanha: 'BRT28 141 28' ✓, linhas inválidas ignoradas")

    # formato livre: texto colado do portal de afiliados
    c = _parse_campaign_entry("Código BRT28 — compras acima de R$ 141,00: R$ 28,00 OFF")
    assert c == {"code": "BRT28", "min_spend": 141.0, "discount": 28.0}
    c = _parse_campaign_entry("BRT56: gaste 282, ganhe 56 de desconto")
    assert c == {"code": "BRT56", "min_spend": 282.0, "discount": 56.0}
    assert _parse_campaign_entry("R$ 28,00 off sem codigo nenhum") is None
    print("  ✅ Formato livre: extrai código/mínimo/desconto de texto colado")

    settings = {
        "import_tax_rate": 0.0,
        "icms_rate": 0.17,
        "coupon_campaigns": [{"code": "BRT28", "min_spend": 141.0, "discount": 28.0}],
    }

    # isola dos cupons descobertos que o bot de produção guarda no banco
    import monitor as monitor_mod
    orig_active = monitor_mod.get_active_coupons
    monitor_mod.get_active_coupons = lambda: []
    try:
        # produto sem cupom próprio → campanha aplica
        # (números do checkout real: app R$ 251,99 − R$ 28 cupom, ICMS 17% por dentro)
        p = {"price": 251.99, "coupon": None}
        _apply_best_coupon(p, settings)
        assert p["coupon"]["code"] == "BRT28"
        assert abs(p["coupon"]["final_price"] - 223.99) < 0.01
        assert abs(_checkout_price(p, settings) - 269.87) < 0.01  # 223.99 / 0.83
        print("  ✅ Checkout do print: 251,99 − 28,00 cupom → final R$ 269,87 (ICMS 17%)")

        # abaixo do gasto mínimo da campanha → nada aplica
        p2 = {"price": 100.0, "coupon": None}
        _apply_best_coupon(p2, settings)
        assert p2["coupon"] is None
        print("  ✅ Abaixo do gasto mínimo: campanha não aplica")

        # cupom do próprio anúncio maior que a campanha → mantém o do anúncio
        p3 = {"price": 251.99, "coupon": {"code": "PONTO40", "discount": 40.0, "min_spend": 0.0,
                                          "applicable": True, "final_price": 211.99}}
        _apply_best_coupon(p3, settings)
        assert p3["coupon"]["code"] == "PONTO40"
        print("  ✅ Cupom do anúncio (R$ 40) vence a campanha (R$ 28)")
    finally:
        monitor_mod.get_active_coupons = orig_active


def test_coupon_harvest():
    print("\n--- Teste: colheita automática de cupons (via banco) ---")
    from database import init_db, get_active_coupons, get_connection
    from monitor import _harvest_coupon, _apply_best_coupon

    init_db()

    # cupom fixo visto num anúncio → vai para o banco
    seen = {"coupon": {"code": "TESTCUP99", "discount": 28.0, "min_spend": 141.0,
                       "fixed": True, "applicable": True, "final_price": 172.0}}
    _harvest_coupon(seen)
    active = {c["code"]: c for c in get_active_coupons()}
    assert "TESTCUP99" in active
    assert active["TESTCUP99"]["discount"] == 28.0
    print("  ✅ Cupom visto num anúncio foi salvo e está ativo")

    # cupom percentual NÃO é colhido (desconto depende do preço do anúncio)
    pct = {"coupon": {"code": "TESTPCT99", "discount": 10.0, "min_spend": 50.0,
                      "fixed": False, "applicable": True, "final_price": 90.0}}
    _harvest_coupon(pct)
    assert "TESTPCT99" not in {c["code"] for c in get_active_coupons()}
    print("  ✅ Cupom percentual não é colhido")

    # outro produto SEM cupom próprio recebe o cupom descoberto
    # (restringe a lista ao cupom de teste para não depender do que o bot de
    # produção já colheu no mesmo banco)
    import monitor as monitor_mod
    rows = [c for c in get_active_coupons() if c["code"] == "TESTCUP99"]
    orig_active = monitor_mod.get_active_coupons
    monitor_mod.get_active_coupons = lambda: rows
    try:
        settings = {"import_tax_rate": 0.0, "icms_rate": 0.17, "coupon_campaigns": []}
        other = {"price": 200.0, "coupon": None}
        _apply_best_coupon(other, settings)
        assert other["coupon"] is not None and other["coupon"]["code"] == "TESTCUP99"
        assert abs(other["coupon"]["final_price"] - 172.0) < 0.01
        print("  ✅ Cupom descoberto aplicado em outro produto (200 − 28 = 172)")
    finally:
        monitor_mod.get_active_coupons = orig_active

    # limpeza
    with get_connection() as conn:
        conn.execute("DELETE FROM coupons WHERE code IN ('TESTCUP99', 'TESTPCT99')")
    print("  ✅ Colheita OK")


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
    from database import init_db, upsert_product, can_post, get_settings, delete_product

    init_db()

    product = {
        "product_id": "TEST_COLD001",
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

    # lógica do monitor: cold start com desconto >= cold_start_threshold (default 30%)
    cold_threshold = get_settings()["cold_start_threshold"] * 100
    should_post = state["is_new"] and product["discount_pct"] >= cold_threshold and can_post(product["product_id"])
    assert should_post is True
    print(f"  ✅ Cold start com {product['discount_pct']}% desconto → posta ✓")

    # produto novo com desconto baixo → NÃO deve postar
    product2 = {**product, "product_id": "TEST_COLD002", "discount_pct": 10.0}
    state2 = upsert_product(product2["product_id"], product2["title"], product2["price"])
    should_post2 = state2["is_new"] and product2["discount_pct"] >= cold_threshold
    assert should_post2 is False
    print(f"  ✅ Cold start com {product2['discount_pct']}% desconto → não posta ✓")

    delete_product("TEST_COLD001")
    delete_product("TEST_COLD002")
    print("  ✅ Cold start logic OK")


def test_telegram_connection():
    print("\n--- Teste: Telegram (conexão real com bot) ---")
    # posta uma mensagem NO CANAL REAL — não pode rodar num `pytest` casual
    if not os.getenv("RUN_TELEGRAM_LIVE_TEST"):
        print("  ⚠️  RUN_TELEGRAM_LIVE_TEST não definido — pulando (evita postar no canal).")
        return
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
    test_coupon_parser()
    test_checkout_total()
    test_checkout_price_target()
    test_campaign_coupons()
    test_coupon_harvest()
    test_telegram_message_format()
    test_cold_start_logic()
    test_telegram_connection()
    print("\n✅ Todos os testes passaram!\n")
