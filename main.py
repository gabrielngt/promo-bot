import schedule
import time
import sys

from config import CHECK_INTERVAL_MINUTES, TELEGRAM_CHANNEL_ID, ALIEXPRESS_APP_KEY
from database import init_db
from monitor import run_check
from telegram_bot import test_connection


def validate_config():
    missing = []
    if not TELEGRAM_CHANNEL_ID or TELEGRAM_CHANNEL_ID == "PREENCHER_DEPOIS":
        missing.append("TELEGRAM_CHANNEL_ID")
    if not ALIEXPRESS_APP_KEY or ALIEXPRESS_APP_KEY == "PREENCHER_DEPOIS":
        missing.append("ALIEXPRESS_APP_KEY")
    return missing


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
