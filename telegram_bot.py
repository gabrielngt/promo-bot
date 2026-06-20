import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _format_message(product: dict, drop_pct: float) -> str:
    stars = "⭐" * round(product["rating"])
    sales_fmt = f"{product['sales']:,}".replace(",", ".")
    price_fmt = f"R$ {product['price']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    original_fmt = f"R$ {product['original_price']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return (
        f"🔥 <b>PROMOÇÃO ALIEXPRESS</b>\n\n"
        f"<b>{product['title']}</b>\n\n"
        f"~~{original_fmt}~~\n"
        f"✅ <b>{price_fmt}</b>  (-{drop_pct:.0f}%)\n\n"
        f"{stars} {product['rating']:.1f}/5  |  📦 {sales_fmt} vendidos\n\n"
        f"👉 <a href=\"{product['link']}\">Comprar no AliExpress</a>"
    )


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

    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)
        result = resp.json()
        if not result.get("ok"):
            print(f"[Telegram] Erro: {result.get('description')}")
            return False
        return True
    except Exception as e:
        print(f"[Telegram] Exceção: {e}")
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
