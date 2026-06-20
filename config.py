import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

ALIEXPRESS_APP_KEY = os.getenv("ALIEXPRESS_APP_KEY")
ALIEXPRESS_APP_SECRET = os.getenv("ALIEXPRESS_APP_SECRET")
ALIEXPRESS_TRACKING_ID = os.getenv("ALIEXPRESS_TRACKING_ID")

CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 60))
PRICE_DROP_THRESHOLD = float(os.getenv("PRICE_DROP_THRESHOLD", 0.15))
MIN_REPOST_DAYS = int(os.getenv("MIN_REPOST_DAYS", 3))

# Categorias do AliExpress para monitorar (periféricos/eletrônicos)
# IDs oficiais: https://portals.aliexpress.com/help/categories.html
CATEGORIES = [
    "44",    # Computer & Office
    "1420",  # Consumer Electronics
    "509",   # Phones & Telecommunications
]

PRODUCTS_PER_CATEGORY = 50
