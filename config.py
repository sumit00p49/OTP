"""
Configuration module for the Telegram Shop Bot.
Loads all settings from environment variables.

MULTI-COUNTRY SUPPORT:
Each country is defined in PRODUCTS as a JSON string in .env.
Format: [{"code":"IN","name":"India","flag":"🇮🇳","price":70,"filters":{...}}, ...]
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

# ==================== Telegram Bot ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ==================== LZT Market API ====================
LZT_API_KEY = os.getenv("LZT_API_KEY", "YOUR_LZT_API_KEY_HERE")
LZT_BASE_URL = os.getenv("LZT_BASE_URL", "https://prod-api.lzt.market")

# ==================== Product Configuration ====================
# JSON array of products/countries. Each entry:
#   code: 2-letter country code for LZT
#   name: Display name
#   flag: Emoji flag
#   price: INR price user pays
#   max_lzt: Max USD to pay on LZT (safety cap)
#   filters: Extra LZT search params (origin, nsb, password, etc.)
#
# FILTERS MAP (from LZT screenshot):
#   "origin[]"          : "resale" / "autoreg" / "personal" / "stealer"
#   "nsb"               : 1 (no spam block only)
#   "sb"                : 1 (spam block only)
#   "telegram_password" : 0 (no password) / 1 (has password)
#   "pmin"              : min price USD
#   "pmax"              : max price USD
#   "not_sold_before"   : 1 (never sold before)

DEFAULT_PRODUCTS = json.dumps([
    {
        "code": "IN",
        "name": "India",
        "flag": "🇮🇳",
        "price": 70,
        "max_lzt": 0.15,
        "filters": {
            "origin[]": "resale",
            "telegram_password": 0
        }
    }
])

PRODUCTS = json.loads(os.getenv("PRODUCTS", DEFAULT_PRODUCTS))

# Legacy single-country (fallback if PRODUCTS not set)
ACCOUNT_PRICE_INR = float(os.getenv("ACCOUNT_PRICE_INR", "70.0"))
MAX_LZT_PRICE_USD = float(os.getenv("MAX_LZT_PRICE_USD", "0.15"))
ACCOUNT_COUNTRY = os.getenv("ACCOUNT_COUNTRY", "IN")

# ==================== Admin Configuration ====================
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))

# ==================== UPI Payment Details ====================
UPI_ID = os.getenv("UPI_ID", "KaizenSeller@ybl")
UPI_NAME = os.getenv("UPI_NAME", "BHARAT LAL GUPTA")
UPI_QR_URL = os.getenv("UPI_QR_URL", "")

# ==================== Deposit ====================
MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", "10.0"))

# ==================== Database ====================
DB_PATH = os.getenv("DB_PATH", "bot_database.db")


def get_product(code: str) -> dict:
    """Get product config by country code."""
    for p in PRODUCTS:
        if p["code"].upper() == code.upper():
            return p
    return PRODUCTS[0] if PRODUCTS else {}
