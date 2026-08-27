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


def test_budget_split_between_stores():
    print("\n--- Teste: orcamento dividido entre as lojas ---")
    # sem reserva, as marcas da AliExpress esgotavam o ciclo e a Shopee nunca rodava
    for max_posts, esperado_shopee in [(2, 1), (3, 1), (5, 2), (10, 5), (1, 1)]:
        shopee_budget = max(1, max_posts // 2)
        ali_budget = max_posts - shopee_budget
        assert shopee_budget == esperado_shopee, (max_posts, shopee_budget)
        assert shopee_budget >= 1, "Shopee sempre tem ao menos 1 vaga"
        assert ali_budget >= 0
        print(f"  orcamento {max_posts:>2} -> AliExpress {ali_budget}, Shopee {shopee_budget}")

    # cenario real do log: 3 deals de marca com orcamento 2
    max_posts = 2
    shopee_budget = max(1, max_posts // 2); ali_budget = max_posts - shopee_budget
    posts = min(3, ali_budget)          # marcas limitadas ao orcamento delas
    assert posts == 1, "marcas nao podem mais consumir o ciclo inteiro"
    assert max_posts - posts >= shopee_budget - 1
    print(f"  caso do log: marcas ficam com {posts}, sobra {max_posts-posts} para a Shopee")


def test_fx_rate_is_cached():
    print("\n--- Teste: cotacao em cache (evita 429) ---")
    import sales
    from database import set_usd_brl_rate, get_usd_brl_rate, get_usd_brl_rate_age_hours

    set_usd_brl_rate(5.11)
    idade = get_usd_brl_rate_age_hours()
    assert idade is not None and idade < 0.1, "acabou de gravar, idade ~0"
    assert abs(get_usd_brl_rate() - 5.11) < 0.001

    # com cotacao fresca, nao chama a API (se chamasse, quebraria aqui)
    chamou = {"n": 0}
    orig = sales.requests.get
    sales.requests.get = lambda *a, **k: (_ for _ in ()).throw(AssertionError("nao devia consultar a API"))
    try:
        assert abs(sales.refresh_usd_brl_rate() - 5.11) < 0.001
        print(f"  OK cotacao com {idade*60:.0f} min nao dispara nova consulta")
    finally:
        sales.requests.get = orig

    assert sales.FX_MAX_AGE_HOURS >= 1
    print(f"  OK so reconsulta apos {sales.FX_MAX_AGE_HOURS}h")


def test_shopee_parser():
    print("\n--- Teste: shopee.parse_product ---")
    import shopee

    # payload real da API (campos confirmados por sondagem)
    raw = {
        "itemId": 15742991199,
        "productName": "Teclado Mecanico TGT Sherman V3",
        "priceMin": "89.99", "priceMax": "89.99",
        "priceDiscountRate": 50,
        "commissionRate": "0.03", "commission": "2.6997",
        "sales": 1499, "ratingStar": "4.9",
        "imageUrl": "https://cf.shopee.com.br/file/abc",
        "offerLink": "https://s.shopee.com.br/ABC123",
        "productLink": "https://shopee.com.br/product/1/2",
        "shopName": "Loja Teste",
    }
    p = shopee.parse_product(raw)
    assert p["store"] == "shopee"
    assert p["product_id"] == "15742991199"
    assert abs(p["price"] - 89.99) < 0.01
    # commissionRate e FRACAO: 0.03 = 3% (nao 0.03%)
    assert abs(p["commission_pct"] - 3.0) < 0.01, "0.03 deve virar 3%"
    assert abs(p["commission_brl"] - 2.6997) < 0.01
    # desconto de 50% reconstroi o preco "de"
    assert abs(p["original_price"] - 179.98) < 0.01
    assert p["has_affiliate"] is True and p["link"].startswith("https://s.shopee.com.br/")
    assert p["rating"] == 4.9 and p["sales"] == 1499
    print(f"  OK R$ {p['price']:.2f} (de R$ {p['original_price']:.2f}) | comissao {p['commission_pct']}%")

    # sem desconto: original == preco (nao inventa "de")
    p2 = shopee.parse_product({**raw, "priceDiscountRate": 0})
    assert abs(p2["original_price"] - p2["price"]) < 0.01
    print("  OK sem desconto: nao inventa preco original")

    # preco invalido -> None
    assert shopee.parse_product({**raw, "priceMin": "0"}) is None
    print("  OK preco zero: None")


def test_shopee_post_has_no_tax():
    print("\n--- Teste: post da Shopee (loja nacional, sem imposto) ---")
    from telegram_bot import _format_message
    p = {
        "store": "shopee", "title": "Teclado Teste", "price": 89.99,
        "original_price": 179.98, "rating": 4.9, "sales": 1499,
        "link": "https://s.shopee.com.br/ABC", "taxes": {"ii": 0.0, "icms": 0.0},
    }
    msg = _format_message(p, 50)
    assert "SHOPEE" in msg.splitlines()[0], "cabecalho deve identificar a loja"
    assert "Comprar na Shopee" in msg
    assert "imposto" not in msg.lower(), "produto nacional nao mostra imposto"
    assert "Total estimado no checkout" not in msg
    print("  OK selo Shopee, CTA correto, sem linha de imposto")


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

    # desconto >= preço: cupom de outra faixa, não aplica (senão preço negativo)
    c = _parse_coupon(raw("Spend BRL 0.00, get BRL 28.19 off", "0"), 10.0)
    assert not c["applicable"], "cupom maior que o preço não pode ser aplicável"
    assert c["final_price"] == 10.0, "preço final nunca fica negativo"
    print("  ✅ Cupom maior que o preço: não aplica (sem preço negativo)")

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

    # linha de central de cupons, com validade — o ano/hora não pode virar "gasto mínimo"
    c = _parse_campaign_entry("AFS3 $3 off $15 2026-08-26 23:59:59")
    assert c == {"code": "AFS3", "min_spend": 15.0, "discount": 3.0}
    c = _parse_campaign_entry("AFS90 $90 off $550 2026-08-26 23:59:59")
    assert c == {"code": "AFS90", "min_spend": 550.0, "discount": 90.0}
    print("  ✅ Data de validade na linha não confunde o cálculo (ano != gasto mínimo)")

    settings = {"import_tax_rate": 0.0, "icms_rate": 0.17}

    # a fonte de campanhas é a tabela coupons; isola dos cupons reais do banco
    import monitor as monitor_mod
    orig_active = monitor_mod.get_active_coupons
    monitor_mod.get_active_coupons = lambda: [
        {"code": "BRT28", "min_spend": 141.0, "discount": 28.0}
    ]
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

        # campanha com desconto >= preço não pode ser aplicada (preço negativo)
        big = {"import_tax_rate": 0.0, "icms_rate": 0.17}
        monitor_mod.get_active_coupons = lambda: [
            {"code": "BIG", "min_spend": 0.0, "discount": 50.0}
        ]
        p4 = {"price": 30.0, "coupon": None}
        _apply_best_coupon(p4, big)
        assert p4["coupon"] is None, "cupom de R$50 não pode aplicar em produto de R$30"
        assert _checkout_price(p4, big) > 0
        print("  ✅ Campanha maior que o preço: ignorada (sem preço negativo)")
    finally:
        monitor_mod.get_active_coupons = orig_active


def test_daily_post_cap():
    print("\n--- Teste: teto diário de posts ---")
    from database import get_settings, count_posts_since

    s = get_settings()
    assert "max_posts_per_day" in s and s["max_posts_per_day"] >= 1
    print(f"  ✅ Setting max_posts_per_day presente: {s['max_posts_per_day']}")

    n = count_posts_since(24)
    assert isinstance(n, int) and n >= 0
    print(f"  ✅ count_posts_since(24) = {n} post(s)")

    # a aritmética que o monitor usa para fechar o ciclo
    for posts_24h, cap, per_cycle, esperado in [
        (0, 20, 5, 5),    # dia limpo → limite do ciclo
        (18, 20, 5, 2),   # perto do teto → só o que falta
        (20, 20, 5, 0),   # no teto → nada
        (72, 20, 5, 0),   # acima do teto (caso do flood) → nada
    ]:
        restante = max(0, cap - posts_24h)
        assert min(per_cycle, restante) == esperado
    print("  ✅ Teto corta o ciclo: 18/20 → 2 posts, 20/20 e 72/20 → 0")


def test_order_parser():
    print("\n--- Teste: aliexpress._parse_order / _extract_date ---")
    from aliexpress import _parse_order, _extract_date

    assert _extract_date("2026-08-15 10:30:00") == "2026-08-15"
    assert _extract_date("2026-08-15T10:30:00Z") == "2026-08-15"
    assert _extract_date(None) is None
    assert _extract_date("data invalida") is None
    print("  ✅ _extract_date: formatos comuns reconhecidos, inválido → None")

    # valores monetários vêm em CENTAVOS (inteiro) — caso real do pedido do teclado
    from aliexpress import _parse_money_field
    assert abs(_parse_money_field("3792") - 37.92) < 0.01
    assert abs(_parse_money_field("113") - 1.13) < 0.01
    assert abs(_parse_money_field("58") - 0.58) < 0.01
    assert abs(_parse_money_field("0") - 0.0) < 0.01
    # se um dia vier com decimal explícito, já está em unidades — não divide
    assert abs(_parse_money_field("37.92") - 37.92) < 0.01
    print("  ✅ _parse_money_field: centavos → unidades (3792 → 37.92), decimal preservado")

    # pedido "pago" (ainda não confirmado) → usa os campos paid_*
    raw_paid = {
        "order_id": "800123", "product_id": "1005006789", "product_title": "Mouse Teste",
        "order_status": "Payment Completed", "paid_amount": "15000", "commission_rate": "5%",
        "estimated_paid_commission": "750", "settled_currency": "USD",
        "created_time": "2026-08-10 12:00:00", "is_new_buyer": "true",
    }
    o = _parse_order(raw_paid)
    assert o["order_id"] == "800123" and o["sub_order_id"] == "800123"  # sem sub_order_id → usa order_id
    assert abs(o["paid_amount"] - 150.0) < 0.01
    assert abs(o["estimated_commission"] - 7.50) < 0.01
    assert o["currency"] == "USD", "moeda vem do settled_currency, não assume BRL"
    assert o["order_date"] == "2026-08-10"
    assert o["is_new_buyer"] is True
    print("  ✅ Pedido 'pago': usa paid_amount/estimated_paid_commission, moeda do dado")

    # pedido "confirmado" → prefere os campos finished_* sobre os paid_*
    raw_finished = {**raw_paid, "sub_order_id": "800123-1",
                    "finished_amount": "14800", "estimated_finished_commission": "740"}
    o2 = _parse_order(raw_finished)
    assert o2["sub_order_id"] == "800123-1"
    assert abs(o2["paid_amount"] - 148.0) < 0.01, "deve preferir finished_amount sobre paid_amount"
    assert abs(o2["estimated_commission"] - 7.40) < 0.01
    print("  ✅ Pedido 'confirmado': prefere finished_amount/estimated_finished_commission")

    # caso real completo: teclado X68HE — 3792 centavos USD, comissão 3%
    real = _parse_order({
        "order_id": "8213456993712551", "sub_order_id": "8213456993722551",
        "product_id": "1005008813162763", "product_title": "X68HE ATTACK SHARK",
        "order_status": "Payment Completed", "paid_amount": "3792",
        "commission_rate": "3.00%", "estimated_paid_commission": "113",
        "settled_currency": "USD", "created_time": "2026-08-17 10:25:47",
    })
    assert abs(real["paid_amount"] - 37.92) < 0.01, "US$ 37,92 (~R$200), não 3792"
    assert abs(real["estimated_commission"] - 1.13) < 0.01
    print(f"  ✅ Caso real: US$ {real['paid_amount']:.2f} / comissão US$ {real['estimated_commission']:.2f}")

    assert _parse_order({}) is None  # sem order_id
    print("  ✅ Pedido sem order_id: None")


def test_sales_sync():
    print("\n--- Teste: sincronização de vendas (via banco) ---")
    from database import init_db, upsert_affiliate_order, get_sales_summary, get_sales_series, get_recent_orders, get_connection
    from datetime import datetime, timezone

    init_db()
    today = datetime.now(timezone.utc).date().isoformat()

    order = {
        "order_id": "TESTORDER1", "sub_order_id": "TESTORDER1", "product_id": "1005099",
        "product_title": "Produto de Teste", "order_status": "Payment Completed",
        "paid_amount": 199.90, "commission_rate": "5%", "estimated_commission": 9.99,
        "currency": "USD", "order_date": today, "created_time_raw": None,
        "paid_time_raw": None, "is_new_buyer": True,
    }
    upsert_affiliate_order(order)

    summary = get_sales_summary(days=30)
    assert summary["count"] >= 1
    assert summary["paid_total"] >= 199.90
    # o resumo não pode zerar por causa da moeda: a comissão é liquidada em USD
    assert summary["currency"] is not None, "resumo deve informar a moeda dos totais"
    print(f"  ✅ Resumo: {summary['count']} venda(s), {summary['currency']} {summary['paid_total']:.2f}")

    series = get_sales_series(days=30)
    today_bucket = next((s for s in series if str(s["order_date"]) == today), None)
    assert today_bucket is not None and today_bucket["count"] >= 1
    print(f"  ✅ Série diária inclui o pedido de hoje: {today_bucket['count']} venda(s)")

    recent = get_recent_orders(limit=10)
    assert any(o["order_id"] == "TESTORDER1" for o in recent)
    print("  ✅ Pedido aparece em get_recent_orders")

    # upsert de novo com valor atualizado (pedido avançou de status) → substitui, não duplica
    upsert_affiliate_order({**order, "order_status": "Buyer Confirmed Receipt", "paid_amount": 189.90})
    recent2 = get_recent_orders(limit=10)
    updated = next(o for o in recent2 if o["order_id"] == "TESTORDER1")
    assert abs(updated["paid_amount"] - 189.90) < 0.01
    assert len([o for o in recent2 if o["order_id"] == "TESTORDER1"]) == 1
    print("  ✅ Upsert atualiza o pedido existente em vez de duplicar")

    # conversão USD -> BRL (a AliExpress liquida em dólar, o painel mostra em real)
    from api import _to_brl
    assert abs(_to_brl(37.92, "USD", 5.40) - 204.77) < 0.01
    assert abs(_to_brl(100.0, "BRL", 5.40) - 100.0) < 0.01, "valor já em BRL não é convertido"
    assert _to_brl(None, "USD", 5.40) == 0.0
    print("  ✅ Conversão: US$ 37,92 → R$ 204,77 (BRL não é convertido de novo)")

    # exclusão manual (compra própria) tira o pedido dos totais
    from database import set_order_excluded
    antes = get_sales_summary(days=30)["count"]
    assert set_order_excluded("TESTORDER1", "TESTORDER1", True) is True
    depois = get_sales_summary(days=30)["count"]
    assert depois == antes - 1, f"excluído deveria sair dos totais ({antes} -> {depois})"
    assert any(o["order_id"] == "TESTORDER1" and o["excluded"] for o in get_recent_orders(10)),         "excluído continua na lista, marcado"
    # re-sync não pode reverter a marcação manual
    upsert_affiliate_order({**order, "paid_amount": 150.0})
    assert get_sales_summary(days=30)["count"] == depois, "re-sync não pode desfazer a exclusão"
    print("  ✅ Exclusão: sai dos totais, fica na lista e sobrevive ao re-sync")

    assert set_order_excluded("TESTORDER1", "TESTORDER1", False) is True
    assert get_sales_summary(days=30)["count"] == antes
    print("  ✅ Reinclusão volta a contar nos totais")

    with get_connection() as conn:
        conn.execute("DELETE FROM affiliate_orders WHERE order_id = 'TESTORDER1'")
    print("  ✅ Sales sync OK")


def test_manual_coupons_and_expiry():
    print("\n--- Teste: cupons manuais, validade e expiracao ---")
    from datetime import datetime, timedelta, timezone
    from database import (init_db, add_manual_coupon, delete_coupon,
                          get_active_coupons, list_coupons)

    init_db()
    agora = datetime.now(timezone.utc)

    # sem validade → sempre ativo
    add_manual_coupon("TESTMAN1", 100.0, 10.0, None)
    ativos = {c["code"] for c in get_active_coupons()}
    assert "TESTMAN1" in ativos
    print("  ✅ Cupom manual sem validade: ativo")

    # validade futura → ativo
    add_manual_coupon("TESTMAN2", 100.0, 10.0, agora + timedelta(days=2))
    assert "TESTMAN2" in {c["code"] for c in get_active_coupons()}
    print("  ✅ Validade futura: ativo")

    # validade passada → sai sozinho de get_active_coupons (não é mais aplicado)
    add_manual_coupon("TESTMAN3", 100.0, 10.0, agora - timedelta(days=1))
    assert "TESTMAN3" not in {c["code"] for c in get_active_coupons()}, "vencido não pode ser aplicado"
    # mas continua visível no painel, marcado como inativo, para o usuário remover
    painel = {c["code"]: c for c in list_coupons()}
    assert "TESTMAN3" in painel and painel["TESTMAN3"]["active"] is False
    print("  ✅ Vencido: sai da aplicação automaticamente, fica visível no painel")

    for code in ("TESTMAN1", "TESTMAN2", "TESTMAN3"):
        assert delete_coupon(code) is True
    assert delete_coupon("NAOEXISTE") is False
    print("  ✅ Remoção OK")


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

    # cupom "gaste X, ganhe X" (desconto >= gasto mínimo) é artefato de parse
    bogus = {"coupon": {"code": "TESTBOGUS", "discount": 16.9, "min_spend": 16.9,
                        "fixed": True, "applicable": True, "final_price": 0.0}}
    _harvest_coupon(bogus)
    assert "TESTBOGUS" not in {c["code"] for c in get_active_coupons()},         "cupom que zera o produto não pode ser propagado"
    print("  ✅ Cupom 'gaste X ganhe X' não é colhido")

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
    test_budget_split_between_stores()
    test_fx_rate_is_cached()
    test_shopee_parser()
    test_shopee_post_has_no_tax()
    test_coupon_parser()
    test_checkout_total()
    test_checkout_price_target()
    test_campaign_coupons()
    test_manual_coupons_and_expiry()
    test_daily_post_cap()
    test_order_parser()
    test_sales_sync()
    test_coupon_harvest()
    test_telegram_message_format()
    test_cold_start_logic()
    test_telegram_connection()
    print("\n✅ Todos os testes passaram!\n")
