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
UPI_ID = os.getenv("UPI_ID", "SurojSeller@fam")
UPI_NAME = os.getenv("UPI_NAME", "SANDIP BERA")
UPI_QR_URL = os.getenv("UPI_QR_URL", "")

# ==================== Deposit ====================
MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", "10.0"))

# ==================== Database ====================
DB_PATH = os.getenv("DB_PATH", "bot_database.db")

# ==================== MongoDB (Products) ====================
# If set, products are stored in MongoDB (persistent across restarts)
# If not set, falls back to local products.json file
MONGO_URI = os.getenv("MONGO_URI", "")


def get_product(code: str) -> dict:
    """Get product config by country code."""
    for p in PRODUCTS:
        if p["code"].upper() == code.upper():
            return p
    return PRODUCTS[0] if PRODUCTS else {}


# ==================== Channel Force Join ====================
# Channel username (without @) that users must join to use bot
# Leave empty to disable force join
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "")

# ==================== Daily Report ====================
# Send daily report at this hour (24h format, server timezone)
DAILY_REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "23"))

# ==================== Bulk Discount ====================
# 5 accounts = ₹10 off total, 10 accounts = ₹20 off total
BULK_DISCOUNT_5 = float(os.getenv("BULK_DISCOUNT_5", "10.0"))
BULK_DISCOUNT_10 = float(os.getenv("BULK_DISCOUNT_10", "20.0"))
