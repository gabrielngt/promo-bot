from config import CATEGORIES, PRODUCTS_PER_CATEGORY
from aliexpress import get_hot_products, get_products_by_brand, parse_product, get_shipping, get_product_detail, search_products, get_featured_promos, get_featured_promo_products
from database import upsert_product, can_post, mark_posted, get_settings, get_watchlist, get_recent_min, save_reactions, get_reactions_offset, set_reactions_offset, prune_price_history, record_check_run, save_coupon, get_active_coupons, count_posts_since
from telegram_bot import post_product, fetch_reaction_updates
from sales import sync_orders

import re
import time
import threading

# Impede que o disparo manual ("Verificar agora") e o scheduler rodem um ciclo
# ao mesmo tempo — dois ciclos concorrentes poderiam postar o mesmo item 2x.
_check_lock = threading.Lock()


def _harvest_coupon(product: dict):
    """Guarda cupons de campanha vistos em anúncios: o código é global, então um
    cupom descoberto num produto pode ser aplicado nos outros posts do ciclo."""
    c = product.get("coupon")
    if c and c.get("fixed") and c["discount"] > 0 and c["min_spend"] > 0:
        save_coupon(c["code"], c["min_spend"], c["discount"])


def _apply_best_coupon(product: dict, settings: dict):
    """Compara o cupom do próprio anúncio com os de campanha (painel + descobertos
    automaticamente) e deixa em product["coupon"] o de maior desconto aplicável.
    Os de campanha são estimativa: a API não expõe elegibilidade por produto."""
    own = product.get("coupon")
    best = own if (own and own.get("applicable")) else None
    campaigns = list(settings.get("coupon_campaigns", [])) + get_active_coupons()
    for camp in campaigns:
        # desconto >= preço = cupom de outra faixa; aplicar daria preço negativo
        if camp["discount"] >= product["price"]:
            continue
        if product["price"] >= camp["min_spend"] and camp["discount"] > (best["discount"] if best else 0.0):
            best = {
                "code": camp["code"],
                "discount": camp["discount"],
                "min_spend": camp["min_spend"],
                "fixed": True,
                "applicable": True,
                "final_price": round(product["price"] - camp["discount"], 2),
            }
    if best:
        product["coupon"] = best


def _checkout_price(product: dict, settings: dict) -> float:
    """Preço final estimado no checkout: cupom aplicado + impostos (II e ICMS).
    Sem frete — ele só é consultado na hora de postar (1 chamada por post)."""
    coupon = product.get("coupon")
    base = coupon["final_price"] if (coupon and coupon["applicable"]) else product["price"]
    icms = settings["icms_rate"]
    if not 0 <= icms < 1:
        icms = 0.0
    return round(base * (1 + settings["import_tax_rate"]) / (1 - icms), 2)


def _post_with_shipping(product: dict, pct: float, settings: dict) -> int | None:
    """Enriquece com frete (só agora, na hora de postar) e posta. Retorna message_id ou None."""
    # sem link de afiliado = sem comissão; não posta (tenta de novo no próximo ciclo)
    if not product.get("has_affiliate"):
        print(f"[Monitor] Sem link de afiliado, pulando: {product['title'][:50]}")
        return None
    shipping = get_shipping(product["product_id"], product.get("sku_id", ""), product["price"])
    if shipping:
        product["shipping"] = shipping
    # melhor cupom (anúncio vs campanhas do painel) e alíquotas para o total
    # estimado no checkout (preço da API vem sem tributos)
    _apply_best_coupon(product, settings)
    product["taxes"] = {"ii": settings["import_tax_rate"], "icms": settings["icms_rate"]}
    return post_product(product, pct)

# Um produto é postado se (a) caiu abaixo do mínimo histórico (queda real) ou
# (b) tem bom desconto sobre o preço original (deal de tabela). O desconto da
# API é notoriamente inflado, então o caminho (b) exige sinais de qualidade
# (avaliação + vendas) antes de postar.
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
    for entry in brands:
        if entry["name"].lower() in t:
            kw_filter = entry.get("keywords", [])
            if not kw_filter:
                return True
            if any(kw.lower() in t for kw in kw_filter):
                return True
    return False


def _passes_quality(product: dict) -> bool:
    return product["rating"] >= COLD_START_MIN_RATING and product["sales"] >= COLD_START_MIN_SALES


def _title_fingerprint(title: str) -> str:
    words = sorted(re.findall(r'[a-z0-9]{3,}', title.lower()))
    return "".join(words)[:60]


def _title_words(title: str) -> set:
    return set(re.findall(r'[a-z0-9]{3,}', title.lower()))


def _title_similarity(a: str, b: str) -> float:
    """Similaridade de Jaccard entre os conjuntos de palavras de dois títulos (0 a 1)."""
    wa, wb = _title_words(a), _title_words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


# Quão parecido um anúncio de outro vendedor precisa ser para contar como o
# "mesmo produto". Mais alto = menos falsos positivos, menos equivalentes achados.
EQUIVALENT_MIN_SIMILARITY = 0.5

# Limiar para considerar dois títulos "o mesmo produto" no dedup de ciclo.
# Mais alto que EQUIVALENT para evitar fundir produtos distintos (ex: mouse vs mousepad).
DEDUP_SIMILARITY = 0.65

# Quantas campanhas em destaque consultar por ciclo (cada uma custa 1 chamada de API).
MAX_PROMOS_PER_CYCLE = 3


def _cheapest_equivalent(product: dict) -> dict:
    """Busca anúncios equivalentes (outros vendedores) e retorna o mais barato entre
    eles e o próprio produto. Marca seller_count com quantos anúncios entraram na conta."""
    candidates = [product]
    # título completo é longo/ruidoso demais como termo de busca; as primeiras
    # palavras (marca + modelo) acham muito mais equivalentes
    query = " ".join(product["title"].split()[:8])
    for raw in search_products(query):
        if str(raw.get("product_id")) == product["product_id"]:
            continue
        alt = parse_product(raw)
        if not alt or alt["price"] <= 0:
            continue
        # anúncio alternativo só vale se rende comissão e tem sinais de confiança
        # (evita trocar o link por um seller ruim só porque está mais barato)
        if not alt.get("has_affiliate") or not _passes_quality(alt):
            continue
        # guarda contra acessórios/capas: preço absurdamente menor não é o mesmo item
        if alt["price"] < product["price"] * 0.3:
            continue
        if _title_similarity(product["title"], alt["title"]) >= EQUIVALENT_MIN_SIMILARITY:
            candidates.append(alt)

    best = min(candidates, key=lambda p: p["price"])
    best["seller_count"] = len(candidates)
    return best


def check_category(category_id: str, settings: dict, posts_so_far: int = 0, raw_products_override: list = None, seen_fingerprints: dict = None) -> int:
    if seen_fingerprints is None:
        seen_fingerprints = {}

    raw_list = raw_products_override if raw_products_override is not None else get_hot_products(category_id, page_size=PRODUCTS_PER_CATEGORY)

    # Dedup local: agrupa por fingerprint E por similaridade de título (Jaccard >= 0.65),
    # mantendo o mais barato por grupo. Pula o que já foi postado neste ciclo.
    cheapest: dict[str, dict] = {}
    for raw in raw_list:
        p = parse_product(raw)
        if not p:
            continue
        _harvest_coupon(p)
        fp = _title_fingerprint(p["title"])

        if fp in seen_fingerprints:
            continue
        if any(_title_similarity(p["title"], t) >= DEDUP_SIMILARITY for t in seen_fingerprints.values()):
            continue

        # Procura bucket existente por similaridade; se não achar, usa o próprio fp.
        bucket = next(
            (efp for efp, ep in cheapest.items() if _title_similarity(p["title"], ep["title"]) >= DEDUP_SIMILARITY),
            fp,
        )
        if bucket not in cheapest or p["price"] < cheapest[bucket]["price"]:
            cheapest[bucket] = p

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

        # baseline = menor preço dos últimos 30 dias (mesma régua da watchlist).
        # O mínimo all-time congelava o produto: um pico de promoção antigo
        # impedia qualquer post futuro por "queda vs mínimo".
        recent_min = get_recent_min(product["product_id"], days=30)
        upsert_product(product["product_id"], product["title"], product["price"], product.get("link", ""))

        baseline = recent_min if recent_min is not None else product["price"]
        drop_pct = (baseline - product["price"]) / baseline * 100 if baseline > 0 else 0.0

        is_drop = drop_pct >= threshold                                   # caiu abaixo do mínimo histórico
        is_discount = product["discount_pct"] >= cold_threshold and _passes_quality(product)  # desconto sobre o original

        if not (is_drop or is_discount):
            continue
        if not can_post(product["product_id"], product["price"]):
            continue

        pct = product["discount_pct"] if is_discount else drop_pct
        motivo = "queda vs mínimo" if is_drop else "desconto vs original"
        print(f"[Monitor] Deal ({motivo}): {product['title'][:50]} | -{pct:.0f}% | R$ {product['price']:.2f}")
        msg_id = _post_with_shipping(product, pct, settings)
        if msg_id:
            mark_posted(product["product_id"], product["price"], msg_id)
            seen_fingerprints[fp] = product["title"]
            posts_made += 1
            time.sleep(2)

    return posts_made


def check_watchlist(settings: dict, max_posts: int, seen_fingerprints: dict) -> int:
    """Re-checa os produtos vigiados (curados pelo usuário). Posta quando o preço
    FINAL (cupom + impostos) atinge o alvo OU quando o preço-base cai abaixo do
    mínimo recente. Sem filtros de qualidade/marca: o usuário escolheu estes itens."""
    watched = get_watchlist()
    if not watched:
        return 0

    print(f"[Monitor] Vigiando {len(watched)} produto(s) da watchlist...")
    threshold = settings["price_drop_threshold"] * 100
    posts_made = 0

    for item in watched:
        if posts_made >= max_posts:
            break

        fresh = get_product_detail(item["product_id"])
        if not fresh:
            continue
        _harvest_coupon(fresh)

        # busca anúncios equivalentes (outros vendedores) e fica com o mais barato
        best = _cheapest_equivalent(fresh)
        current = best["price"]

        # baseline = menor preço dos últimos 30 dias (janela móvel), lido ANTES de
        # gravar a leitura de agora — evita que a régua só caia e trave o item.
        recent_min = get_recent_min(fresh["product_id"], days=30)

        # histórico e cooldown ficam sob o produto vigiado (1 linha no banco),
        # mas o preço/link rastreados são os do anúncio mais barato encontrado.
        upsert_product(fresh["product_id"], fresh["title"], current, best.get("link", ""))
        target = item.get("target_price")
        baseline = recent_min if recent_min is not None else current
        drop_pct = (baseline - current) / baseline * 100 if baseline > 0 else 0.0

        # o alvo é comparado com o preço FINAL (cupom + impostos), que é o que
        # o usuário paga; o histórico/queda continua no preço-base da API.
        _apply_best_coupon(best, settings)
        final_price = _checkout_price(best, settings)
        hit_target = target is not None and final_price <= target
        is_drop = drop_pct >= threshold

        if not (hit_target or is_drop):
            continue
        if not can_post(fresh["product_id"], current):
            continue

        alt_note = f" | {best['seller_count']} anúncios" if best.get("seller_count", 1) > 1 else ""
        motivo = f"final R$ {final_price:.2f} atingiu alvo R$ {target:.2f}" if hit_target else "queda vs mínimo"
        print(f"[Monitor] Watchlist ({motivo}): {fresh['title'][:50]} | R$ {current:.2f}{alt_note}")
        msg_id = _post_with_shipping(best, drop_pct, settings)
        if msg_id:
            mark_posted(fresh["product_id"], current, msg_id)
            seen_fingerprints[_title_fingerprint(fresh["title"])] = fresh["title"]
            posts_made += 1
            time.sleep(2)

    return posts_made


_POSITIVE_REACTIONS = {"🔥", "👍", "❤", "❤️", "🎉", "🤩"}
_NEGATIVE_REACTIONS = {"👎", "🤮", "💩"}


def poll_reactions():
    """Busca updates de reações do Telegram e persiste contagens no banco."""
    offset = get_reactions_offset()
    updates, next_offset = fetch_reaction_updates(offset)
    if next_offset != offset:
        set_reactions_offset(next_offset)
    for u in updates:
        rc = u["message_reaction_count"]
        msg_id = rc["message_id"]
        positive = sum(
            r["total_count"] for r in rc.get("reactions", [])
            if r.get("type", {}).get("emoji") in _POSITIVE_REACTIONS
        )
        negative = sum(
            r["total_count"] for r in rc.get("reactions", [])
            if r.get("type", {}).get("emoji") in _NEGATIVE_REACTIONS
        )
        save_reactions(msg_id, positive, negative)
        if positive or negative:
            print(f"[Reactions] msg_id={msg_id} 👍{positive} 👎{negative}")


def run_check():
    # non-blocking: se um ciclo já roda, ignora o disparo em vez de enfileirar
    if not _check_lock.acquire(blocking=False):
        print("[Monitor] Ciclo já em execução — disparo ignorado.")
        return 0
    try:
        return _do_check()
    finally:
        _check_lock.release()


def _do_check():
    settings = get_settings()

    if not settings["monitoring_enabled"]:
        print("[Monitor] Monitoramento desativado no painel — ciclo ignorado.")
        return 0

    # marca o início do ciclo: "última verificação" no painel fica responsiva
    # (um ciclo completo leva minutos; esperar o fim deixava o card defasado)
    record_check_run()

    if not settings["filters_enabled"]:
        print("[Monitor] Filtros desativados — sem restrição de keyword/blacklist/marca.")
        settings = {**settings, "peripheral_keywords": [], "keyword_blacklist": [], "brand_whitelist": []}

    brands = settings["brand_whitelist"]

    # Teto diário: segura o canal quando algo faz muitos produtos parecerem em
    # promoção de uma vez (ex.: mudança na fonte do preço deslocando o histórico).
    posts_24h = count_posts_since(24)
    daily_left = settings["max_posts_per_day"] - posts_24h
    if daily_left <= 0:
        print(f"[Monitor] Teto diário atingido ({posts_24h}/{settings['max_posts_per_day']} posts em 24h) — ciclo ignorado.")
        return 0
    max_posts = min(settings["max_posts_per_cycle"], daily_left)

    total_posts = 0
    seen_fingerprints: dict = {}  # só fingerprints já POSTADOS neste ciclo

    # Watchlist tem prioridade — itens escolhidos a dedo pelo usuário.
    total_posts += check_watchlist(settings, max_posts, seen_fingerprints)

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

    # Campanhas oficiais em destaque (Flash Deals, Choice Day...) preenchem o que
    # sobrar — produtos com promoção de evento real, não só desconto de tabela.
    if total_posts < max_posts:
        promos = get_featured_promos()
        if promos:
            print(f"[Monitor] Verificando {min(len(promos), MAX_PROMOS_PER_CYCLE)} campanha(s) em destaque...")
        for promo in promos[:MAX_PROMOS_PER_CYCLE]:
            if total_posts >= max_posts:
                break
            promo_name = promo.get("promo_name")
            if not promo_name:
                continue
            raw_products = get_featured_promo_products(promo_name)
            if raw_products:
                total_posts += check_category(
                    category_id=f"promo:{promo_name}",
                    settings=settings,
                    posts_so_far=total_posts,
                    raw_products_override=raw_products,
                    seen_fingerprints=seen_fingerprints,
                )
            time.sleep(1)

    print(f"[Monitor] Verificação concluída. {total_posts} promoções postadas.")
    poll_reactions()
    prune_price_history()
    try:
        sync_orders()
    except Exception as e:
        print(f"[Sales] Erro ao sincronizar pedidos: {e}")
    return total_posts
