import schedule
import time
import sys

from config import (
    CHECK_INTERVAL_MINUTES, TELEGRAM_CHANNEL_ID,
    ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET, ALIEXPRESS_TRACKING_ID,
)
from database import init_db
from monitor import run_check
from telegram_bot import test_connection

_PLACEHOLDER = "PREENCHER_DEPOIS"


def validate_config():
    checks = {
        "TELEGRAM_CHANNEL_ID": TELEGRAM_CHANNEL_ID,
        "ALIEXPRESS_APP_KEY": ALIEXPRESS_APP_KEY,
        "ALIEXPRESS_APP_SECRET": ALIEXPRESS_APP_SECRET,
        "ALIEXPRESS_TRACKING_ID": ALIEXPRESS_TRACKING_ID,
    }
    return [k for k, v in checks.items() if not v or v == _PLACEHOLDER]


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
    init_db()

    print("[Init] Testando conexão com o Telegram...")
    if not test_connection():
        print("❌ Falha na conexão com o Telegram. Verifique o token e o ID do canal.")
        sys.exit(1)
    print("✅ Telegram OK\n")

    # primeira execução imediata
    run_check()

    # agenda execuções periódicas
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(run_check)
    print(f"\n[Scheduler] Rodando a cada {CHECK_INTERVAL_MINUTES} minutos. Ctrl+C para parar.\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
