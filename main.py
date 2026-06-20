import schedule
import time
import sys
import threading

import uvicorn

from config import (
    CHECK_INTERVAL_MINUTES, TELEGRAM_CHANNEL_ID,
    ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET, ALIEXPRESS_TRACKING_ID, ADMIN_API_KEY,
)
from database import init_db, get_settings
from monitor import run_check
from telegram_bot import test_connection
from api import app as fastapi_app

_PLACEHOLDER = "PREENCHER_DEPOIS"


def validate_config():
    checks = {
        "TELEGRAM_CHANNEL_ID": TELEGRAM_CHANNEL_ID,
        "ALIEXPRESS_APP_KEY": ALIEXPRESS_APP_KEY,
        "ALIEXPRESS_APP_SECRET": ALIEXPRESS_APP_SECRET,
        "ALIEXPRESS_TRACKING_ID": ALIEXPRESS_TRACKING_ID,
        "ADMIN_API_KEY": ADMIN_API_KEY,
    }
    return [k for k, v in checks.items() if not v or v == _PLACEHOLDER]


def run_api_server():
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8080, log_level="warning")


def run_scheduler():
    settings = get_settings()
    interval = settings["check_interval_minutes"]

    run_check()

    schedule.every(interval).minutes.do(run_check)
    print(f"[Scheduler] Rodando a cada {interval} minutos. Ctrl+C para parar.\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


def main():
    print("=" * 50)
    print("  Promo Bot - AliExpress → Telegram")
    print("=" * 50)

    missing = validate_config()
    if missing:
        print(f"\n⚠️  Credenciais faltando no .env: {', '.join(missing)}")
        print("Preencha o arquivo .env e tente novamente.\n")
        sys.exit(1)

    print("\n[Init] Inicializando banco de dados...")
    from config import PERIPHERAL_KEYWORDS
    init_db(keyword_defaults=PERIPHERAL_KEYWORDS)

    print("[Init] Testando conexão com o Telegram...")
    if not test_connection():
        print("❌ Falha na conexão com o Telegram. Verifique o token e o ID do canal.")
        sys.exit(1)
    print("✅ Telegram OK")

    print("[Init] Iniciando API web na porta 8080...")
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    print("✅ API OK\n")

    run_scheduler()


if __name__ == "__main__":
    main()
