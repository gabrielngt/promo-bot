import re
import time
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Remessa Conforme: 20% Imposto de Importação cobrado pela plataforma no checkout.
# Aplicado sobre o preço final após cupom e moedas.
BR_TAX_RATE = 0.20


def _brl(amount: float) -> str:
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_message(product: dict, drop_pct: float) -> str:
    stars = "⭐" * round(product["rating"])
    sales_fmt = f"{product['sales']:,}".replace(",", ".")

    price = product["price"]
    original_price = product["original_price"]
    coupon = product.get("coupon_amount", 0.0)
    coin = product.get("coin_discount", 0.0)

    price_after_coupon = max(0.0, price - coupon)
    price_after_coins = max(0.0, price_after_coupon - coin)
    final_price = price_after_coins * (1 + BR_TAX_RATE)

    title = product["title"][:150]  # caption Telegram: limite 1024 chars

    lines = [
        "🔥 <b>PROMOÇÃO ALIEXPRESS</b>",
        "",
        f"<b>{title}</b>",
        "",
        f"<s>{_brl(original_price)}</s>",
        f"✅ <b>{_brl(price)}</b>  (-{drop_pct:.0f}%)",
    ]

    if coupon > 0:
        lines.append(f"🎟 Cupom: -{_brl(coupon)} → <b>{_brl(price_after_coupon)}</b>")

    if coin > 0:
        lines.append(f"🪙 Moedas: -{_brl(coin)} → <b>{_brl(price_after_coins)}</b>")

    lines += [
        f"🇧🇷 Est. c/ impostos: <b>{_brl(final_price)}</b>",
        "",
        f"{stars} {product['rating']:.1f}/5  |  📦 {sales_fmt} vendidos",
        "",
        f'👉 <a href="{product["link"]}">Comprar no AliExpress</a>',
    ]

    return "\n".join(lines)


def post_product(product: dict, drop_pct: float) -> bool:
    """Posts a product to the Telegram channel. Returns True on success."""
    text = _format_message(product, drop_pct)
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

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
            if resp.json().get("ok"):
                return True
        except Exception:
            pass  # cai para sendMessage abaixo

    for attempt in range(3):
        try:
            resp = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)
            result = resp.json()
            if result.get("ok"):
                return True
            description = result.get("description", "")
            match = re.search(r"retry after (\d+)", description)
            if match:
                wait = int(match.group(1)) + 1
                print(f"[Telegram] Rate limit — aguardando {wait}s (tentativa {attempt+1}/3)")
                time.sleep(wait)
                continue
            print(f"[Telegram] Erro: {description}")
            return False
        except Exception as e:
            print(f"[Telegram] Exceção: {e}")
            return False
    return False


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
                "text": "✅ Bot de promoções iniciado e conectado!",
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
