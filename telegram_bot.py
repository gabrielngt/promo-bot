import html
import re
import time
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# O preço da API vem SEM os tributos que o AliExpress soma no checkout
# (Remessa Conforme). O post estima o total: (preço + frete) × (1 + II) ÷ (1 − ICMS),
# com alíquotas configuráveis no painel (product["taxes"], vindo dos settings).


def _brl(amount: float) -> str:
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_message(product: dict, drop_pct: float) -> str:
    price = product["price"]
    original_price = product["original_price"]
    coupon = product.get("coupon")

    title = html.escape(product["title"][:150])  # caption Telegram: limite 1024 chars
    link = html.escape(product["link"])

    lines = [
        "🔥 <b>PROMOÇÃO ALIEXPRESS</b>",
        "",
        f"<b>{title}</b>",
        "",
    ]

    # preço original riscado só quando há desconto de verdade
    if original_price > price + 0.01:
        lines.append(f"<s>{_brl(original_price)}</s>")
    price_line = f"✅ <b>{_brl(price)}</b>"
    if drop_pct >= 1:
        price_line += f"  (-{drop_pct:.0f}%)"
    lines.append(price_line)

    if coupon:
        code = html.escape(coupon["code"])
        if coupon["applicable"]:
            lines.append(
                f"🎟 Cupom <code>{code}</code>: -{_brl(coupon['discount'])} → "
                f"<b>{_brl(coupon['final_price'])}</b>"
            )
        elif coupon["discount"] > 0:
            lines.append(
                f"🎟 Cupom <code>{code}</code>: -{_brl(coupon['discount'])} "
                f"(pedidos acima de {_brl(coupon['min_spend'])})"
            )
        else:
            lines.append(f"🎟 Cupom <code>{code}</code> disponível")

    base = coupon["final_price"] if (coupon and coupon["applicable"]) else price
    shipping = product.get("shipping")
    fee = shipping["fee"] if shipping else 0.0
    if shipping:
        days = shipping.get("max_days") or shipping.get("min_days")
        prazo = f" · chega em ~{days} dias" if days else ""
        if fee > 0:
            lines.append(f"🚚 Frete: {_brl(fee)}{prazo}")
        else:
            lines.append(f"🚚 Frete grátis{prazo}")

    taxes = product.get("taxes") or {}
    ii, icms = taxes.get("ii", 0.0), taxes.get("icms", 0.0)
    if (ii > 0 or icms > 0) and icms < 1:
        total = (base + fee) * (1 + ii) / (1 - icms)
        sem_frete = "" if shipping else " + frete"
        lines.append(f"💳 Total estimado no checkout: <b>{_brl(total)}</b>{sem_frete} (impostos inclusos)")
    elif fee > 0:
        lines.append(f"💰 Total com frete: <b>{_brl(base + fee)}</b>")

    seller_count = product.get("seller_count", 1)
    if seller_count > 1:
        lines.append(f"🔎 Menor preço entre {seller_count} anúncios")

    # avaliação/vendas só quando existem — "0.0/5 | 0 vendidos" espanta comprador
    social = []
    if product["rating"] > 0:
        stars = "⭐" * round(product["rating"])
        social.append(f"{stars} {product['rating']:.1f}/5")
    if product["sales"] > 0:
        sales_fmt = f"{product['sales']:,}".replace(",", ".")
        social.append(f"📦 {sales_fmt} vendidos")
    if social:
        lines += ["", "  |  ".join(social)]

    lines += [
        "",
        f'👉 <a href="{link}">Comprar no AliExpress</a>',
    ]

    return "\n".join(lines)


def post_product(product: dict, drop_pct: float) -> int | None:
    """Posts a product to the Telegram channel. Returns message_id on success, None on failure."""
    text = _format_message(product, drop_pct)

    # tenta com foto primeiro, cai para texto simples se não tiver imagem
    if product.get("image_url"):
        try:
            resp = requests.post(
                f"{TELEGRAM_API}/sendPhoto",
                json={
                    "chat_id": TELEGRAM_CHANNEL_ID,
                    "photo": product["image_url"],
                    "caption": text,
                    "parse_mode": "HTML",
                },
                timeout=15,
            )
            data = resp.json()
            if data.get("ok"):
                return data["result"]["message_id"]
        except Exception:
            pass  # cai para sendMessage abaixo

    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    for attempt in range(3):
        try:
            resp = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)
            result = resp.json()
            if result.get("ok"):
                return result["result"]["message_id"]
            description = result.get("description", "")
            match = re.search(r"retry after (\d+)", description)
            if match:
                wait = int(match.group(1)) + 1
                print(f"[Telegram] Rate limit — aguardando {wait}s (tentativa {attempt+1}/3)")
                time.sleep(wait)
                continue
            print(f"[Telegram] Erro: {description}")
            return None
        except Exception as e:
            print(f"[Telegram] Exceção: {e}")
            return None
    return None


def fetch_reaction_updates(offset: int = 0) -> tuple[list[dict], int]:
    """Busca updates de contagem de reações do canal. Retorna (updates, próximo offset)."""
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/getUpdates",
            json={"offset": offset, "allowed_updates": ["message_reaction_count"], "timeout": 0},
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            return [], offset
        updates = data["result"]
        if not updates:
            return [], offset
        return [u for u in updates if "message_reaction_count" in u], updates[-1]["update_id"] + 1
    except Exception:
        return [], offset


def send_admin_message(text: str):
    """Sends a plain text message to the channel (for logs/alerts)."""
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": TELEGRAM_CHANNEL_ID, "text": text},
            timeout=10,
        )
    except Exception:
        pass


def test_connection() -> bool:
    """Checks if the bot token is valid and the channel is reachable."""
    try:
        resp = requests.get(f"{TELEGRAM_API}/getMe", timeout=10)
        bot_ok = resp.json().get("ok", False)
        if not bot_ok:
            print("[Telegram] Token inválido.")
            return False

        # getChat verifica acesso ao canal sem postar nada
        resp2 = requests.post(
            f"{TELEGRAM_API}/getChat",
            json={"chat_id": TELEGRAM_CHANNEL_ID},
            timeout=10,
        )
        ok = resp2.json().get("ok", False)
        if not ok:
            print(f"[Telegram] Sem acesso ao canal: {resp2.json().get('description')}")
        return ok
    except Exception as e:
        print(f"[Telegram] Erro de conexão: {e}")
        return False
