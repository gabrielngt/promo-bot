import html
import re
import time
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Remessa Conforme (2026): II federal removido para compras < US$50.
# O preço retornado pela API já inclui o ICMS (~20%) — nenhum imposto adicional.


def _brl(amount: float) -> str:
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_message(product: dict, drop_pct: float) -> str:
    stars = "⭐" * round(product["rating"])
    sales_fmt = f"{product['sales']:,}".replace(",", ".")

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
        f"<s>{_brl(original_price)}</s>",
        f"✅ <b>{_brl(price)}</b>  (-{drop_pct:.0f}%)",
    ]

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

    shipping = product.get("shipping")
    if shipping:
        fee = shipping["fee"]
        days = shipping.get("max_days") or shipping.get("min_days")
        prazo = f" · chega em ~{days} dias" if days else ""
        if fee > 0:
            base = coupon["final_price"] if (coupon and coupon["applicable"]) else price
            lines.append(f"🚚 Frete: {_brl(fee)}{prazo}")
            lines.append(f"💰 Total com frete: <b>{_brl(base + fee)}</b>")
        else:
            lines.append(f"🚚 Frete grátis{prazo}")

    seller_count = product.get("seller_count", 1)
    if seller_count > 1:
        lines.append(f"🔎 Menor preço entre {seller_count} anúncios")

    lines += [
        f"🇧🇷 Sem II federal · ICMS ~20% incluso",
        "",
        f"{stars} {product['rating']:.1f}/5  |  📦 {sales_fmt} vendidos",
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

        resp2 = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHANNEL_ID,
                "text": "Bot de promoções iniciado e conectado!",
            },
            timeout=10,
        )
        ok = resp2.json().get("ok", False)
        if not ok:
            print(f"[Telegram] Não conseguiu postar no canal: {resp2.json().get('description')}")
        return ok
    except Exception as e:
        print(f"[Telegram] Erro de conexão: {e}")
        return False
