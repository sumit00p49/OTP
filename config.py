"""
Configuration module for the Telegram Shop Bot.
Loads all settings from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ==================== Telegram Bot ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ==================== LZT Market API ====================
# Correct production base URL (verified from lzt-market.readme.io)
LZT_API_KEY = os.getenv("LZT_API_KEY", "YOUR_LZT_API_KEY_HERE")
LZT_BASE_URL = os.getenv("LZT_BASE_URL", "https://prod-api.lzt.market")
# Category slug for Telegram accounts
LZT_CATEGORY = os.getenv("LZT_CATEGORY", "telegram")
# Buy method: "fastbuy" (atomic, 1 call) or "reserve" (reserve -> confirm)
BUY_METHOD = os.getenv("BUY_METHOD", "fastbuy").lower()

# ==================== Admin Configuration ====================
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))

# ==================== UPI Payment Details ====================
UPI_ID = os.getenv("UPI_ID", "KaizenSeller@ybl")
UPI_NAME = os.getenv("UPI_NAME", "Kaizen Seller")


# ==================== Currency Conversion ====================
# LZT charges in RUB/USD/EUR. Wallet is in INR. These are the
# conversion rates (1 unit of foreign currency = X INR).
# Sensible defaults — adjust to current market rates.
USD_TO_INR = float(os.getenv("USD_TO_INR", "85.0"))
RUB_TO_INR = float(os.getenv("RUB_TO_INR", "1.10"))
EUR_TO_INR = float(os.getenv("EUR_TO_INR", "92.0"))

# Profit markup added on top of the converted LZT price (percent).
MARKUP_PERCENT = float(os.getenv("MARKUP_PERCENT", "30.0"))

# ==================== Pricing (fallback / fixed mode) ====================
# Pricing mode: "dynamic" (real LZT price + markup) or "fixed" (flat INR).
PRICE_MODE = os.getenv("PRICE_MODE", "dynamic").lower()
# Used only when PRICE_MODE == "fixed" or as a display hint.
CHEAP_ACC_PRICE = float(os.getenv("CHEAP_ACC_PRICE", "30.0"))
GOOD_ACC_PRICE = float(os.getenv("GOOD_ACC_PRICE", "60.0"))

# Max price (INR) to search for, protects against buying expensive accounts.
MAX_ACC_PRICE_INR = float(os.getenv("MAX_ACC_PRICE_INR", "500.0"))

# ==================== Deposit ====================
MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", "10.0"))

# ==================== Database ====================
DB_PATH = os.getenv("DB_PATH", "bot_database.db")
