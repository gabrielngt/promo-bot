import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

ALIEXPRESS_APP_KEY = os.getenv("ALIEXPRESS_APP_KEY")
ALIEXPRESS_APP_SECRET = os.getenv("ALIEXPRESS_APP_SECRET")
ALIEXPRESS_TRACKING_ID = os.getenv("ALIEXPRESS_TRACKING_ID")

CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 60))
PRICE_DROP_THRESHOLD = float(os.getenv("PRICE_DROP_THRESHOLD", 0.15))
MIN_REPOST_DAYS = int(os.getenv("MIN_REPOST_DAYS", 3))

# Categorias do AliExpress para monitorar
CATEGORIES = [
    "44",    # Computer & Office
    "1420",  # Consumer Electronics
]

PRODUCTS_PER_CATEGORY = 50

# Filtro de periféricos — PT / EN / ZH
# Produto só é postado se o título contiver ao menos uma dessas palavras
PERIPHERAL_KEYWORDS = [
    # teclado
    "teclado", "keyboard", "键盘",
    # mouse
    "mouse", "mice", "鼠标",
    # mousepad / pad
    "mousepad", "mouse pad", "desk pad", "鼠标垫",
    # headset / fone
    "headset", "fone", "headphone", "earphone", "earbuds", "fone de ouvido",
    "耳机", "耳麦",
    # monitor
    "monitor", "display", "显示器",
    # webcam
    "webcam", "web cam", "摄像头",
    # controle / gamepad
    "controle", "gamepad", "joystick", "controller", "手柄", "游戏手柄",
    # microfone
    "microfone", "microphone", "麦克风",
    # gabinete / pc case
    "gabinete", "pc case", "tower case", "机箱",
    # cooler / fan
    "cooler", "cooling fan", "散热",
    # cadeira gamer
    "cadeira gamer", "gaming chair", "游戏椅",
    # hub / adaptador
    "hub usb", "usb hub", "adaptador", "docking", "集线器",
    # cabo
    "cabo hdmi", "hdmi cable", "cabo displayport", "hdmi线",
    # SSD / HD externo
    "ssd", "hd externo", "pendrive", "flash drive", "固态硬盘", "u盘",
]
