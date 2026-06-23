import os
import schedule
import time
import threading

import uvicorn

from config import (
    TELEGRAM_CHANNEL_ID,
    ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET, ALIEXPRESS_TRACKING_ID, ADMIN_API_KEY,
    PERIPHERAL_KEYWORDS,
)
from database import init_db, get_settings
from monitor import run_check
from telegram_bot import test_connection
from api import app as fastapi_app

_PLACEHOLDER = "PREENCHER_DEPOIS"


def _missing_credentials():
    checks = {
        "TELEGRAM_CHANNEL_ID": TELEGRAM_CHANNEL_ID,
        "ALIEXPRESS_APP_KEY": ALIEXPRESS_APP_KEY,
        "ALIEXPRESS_APP_SECRET": ALIEXPRESS_APP_SECRET,
        "ALIEXPRESS_TRACKING_ID": ALIEXPRESS_TRACKING_ID,
    }
    return [k for k, v in checks.items() if not v or v == _PLACEHOLDER]


def run_api_server():
    port = int(os.getenv("PORT", 8080))
    print(f"[API] Iniciando na porta {port}...", flush=True)
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port, log_level="info")


def run_scheduler():
    run_check()
    last_interval = None
    while True:
        interval = get_settings()["check_interval_minutes"]
        if interval != last_interval:
            schedule.clear()
            schedule.every(interval).minutes.do(run_check)
            print(f"[Scheduler] Intervalo: {interval} minutos.", flush=True)
            last_interval = interval
        schedule.run_pending()
        time.sleep(30)


def main():
    print("=" * 50, flush=True)
    print("  Promo Bot - AliExpress → Telegram", flush=True)
    print("=" * 50, flush=True)

    from database import DB_PATH
    print(f"[Init] Banco de dados: {DB_PATH}", flush=True)
    init_db(keyword_defaults=PERIPHERAL_KEYWORDS)
    print("[Init] Banco OK", flush=True)

    # API sempre sobe — painel web fica disponível mesmo sem credenciais do bot
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    missing = _missing_credentials()
    if missing:
        print(f"[Bot] ⚠️  Credenciais pendentes: {', '.join(missing)}", flush=True)
        print("[Bot] Scheduler desativado até as credenciais serem configuradas.", flush=True)
        print("[Bot] API web continua rodando normalmente.", flush=True)
        # mantém o processo vivo para a API continuar servindo
        while True:
            time.sleep(60)

    print("[Bot] Testando conexão com o Telegram...", flush=True)
    if not test_connection():
        print("[Bot] ❌ Falha no Telegram. Verifique TELEGRAM_BOT_TOKEN e TELEGRAM_CHANNEL_ID.", flush=True)
        while True:
            time.sleep(60)

    print("[Bot] ✅ Telegram OK", flush=True)
    run_scheduler()


if __name__ == "__main__":
    main()
