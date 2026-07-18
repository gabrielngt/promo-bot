"""
Diagnóstico da watchlist — somente leitura, NÃO posta e NÃO grava nada.

Para cada produto vigiado, consulta o preço ao vivo na AliExpress e mostra
por que ele postaria (ou não) neste momento, espelhando exatamente a lógica
de check_watchlist. Rode com o .env local:

    python diagnose_watchlist.py
"""
import sys
from dotenv import load_dotenv

load_dotenv()
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from database import get_watchlist, get_recent_min, get_settings, can_post
from aliexpress import get_product_detail
from monitor import _cheapest_equivalent, _checkout_price


def main():
    settings = get_settings()
    threshold = settings["price_drop_threshold"] * 100
    mon = settings["monitoring_enabled"]

    watched = get_watchlist()
    print(f"\nMonitoramento: {'ATIVO' if mon else 'PAUSADO (não posta nada)'}")
    print(f"Vigiados: {len(watched)} | queda mínima p/ postar: {threshold:.1f}%\n")
    if not watched:
        print("Nenhum produto vigiado.")
        return

    would_post = 0
    for item in watched:
        pid = str(item["product_id"])
        title = (item.get("title") or "")[:55]
        target = item.get("target_price")
        print(f"── {title}  (#{pid})")

        fresh = get_product_detail(pid)
        if not fresh:
            print("   ❌ get_product_detail() = None — a API não devolveu este item.")
            print("      Sem isso ele NUNCA posta. Causas: ID inválido, item fora do ar,")
            print("      ou sua conta não tem acesso a 'productdetail.get' (API Advanced).\n")
            continue

        best = _cheapest_equivalent(fresh)
        fresh_price = fresh["price"]
        current = best["price"]
        n = best.get("seller_count", 1)

        recent_min = get_recent_min(pid, days=30)
        baseline = recent_min if recent_min is not None else current
        drop_pct = (baseline - current) / baseline * 100 if baseline > 0 else 0.0

        final_price = _checkout_price(best, settings)
        hit_target = target is not None and final_price <= target
        is_drop = drop_pct >= threshold
        affiliate = bool(best.get("has_affiliate"))
        postable = can_post(pid, current)

        print(f"   preço atual: R$ {current:.2f}" + (f"  (menor entre {n} anúncios; original R$ {fresh_price:.2f})" if n > 1 else ""))
        print(f"   preço final: R$ {final_price:.2f}  (cupom + impostos; é este que vale contra o alvo)")
        print(f"   alvo:        " + (f"R$ {target:.2f}" if target is not None else "— (sem alvo definido)"))
        print(f"   mínimo 30d:  " + (f"R$ {recent_min:.2f}" if recent_min is not None else "— (sem histórico ainda)"))
        print(f"   queda vs mínimo: {drop_pct:+.1f}%  (precisa ser ≥ {threshold:.1f}%)")
        print(f"   link de afiliado: {'sim' if affiliate else 'NÃO — não posta (sem comissão)'}")
        print(f"   cooldown: {'ok, pode postar' if postable else 'em espera (postou recentemente)'}")

        blockers = []
        if not (hit_target or is_drop):
            blockers.append("sem deal (não atingiu alvo nem caiu o suficiente)")
        if not affiliate:
            blockers.append("sem link de afiliado")
        if not postable:
            blockers.append("cooldown de repost")
        if not mon:
            blockers.append("monitoramento pausado")

        if not blockers:
            would_post += 1
            motivo = "atingiu o alvo" if hit_target else "queda vs mínimo"
            print(f"   ✅ POSTARIA AGORA ({motivo})\n")
        else:
            print(f"   ⏸  não posta: {'; '.join(blockers)}\n")

    print(f"Resumo: {would_post} de {len(watched)} vigiado(s) postariam agora.")
    if would_post == 0:
        print("Se todos estão em 'sem deal', a watchlist está correta — só não há promoção no momento.")
        print("Se algum mostra 'get_product_detail = None', esse é o problema a investigar.")


if __name__ == "__main__":
    main()
