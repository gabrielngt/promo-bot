"""Sincroniza pedidos e comissão de afiliado (AliExpress) com o banco.

Roda a cada ciclo do monitor (ver monitor._do_check). Comissão de afiliado
demora a fechar (o comprador pode levar semanas até "confirmar recebimento"),
então a cada sync busca de novo uma janela dos últimos SYNC_WINDOW_DAYS — o
upsert por (order_id, sub_order_id) atualiza o status/valor de pedidos já
vistos conforme eles avançam de "pago" para "confirmado".
"""
from datetime import datetime, timedelta, timezone

from aliexpress import get_affiliate_orders
from database import upsert_affiliate_order

# Documentados pela API; o parâmetro "status" é obrigatório e não aceita lista
# nem vazio, então consultamos um de cada vez.
ORDER_STATUSES = ["Payment Completed", "Buyer Confirmed Receipt"]

SYNC_WINDOW_DAYS = 60
MAX_PAGES_PER_STATUS = 20  # trava de segurança contra paginação mal-formada


def sync_orders() -> int:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=SYNC_WINDOW_DAYS)
    start_s = start.strftime("%Y-%m-%d %H:%M:%S")
    end_s = end.strftime("%Y-%m-%d %H:%M:%S")

    total = 0
    for status in ORDER_STATUSES:
        page_index = None
        for _ in range(MAX_PAGES_PER_STATUS):
            orders, page_index = get_affiliate_orders(start_s, end_s, status, page_index=page_index)
            for o in orders:
                upsert_affiliate_order(o)
                total += 1
            if not page_index or not orders:
                break

    if total:
        print(f"[Sales] {total} pedido(s) sincronizado(s).")
    return total
