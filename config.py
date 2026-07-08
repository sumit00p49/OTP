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
# Get your token from: https://lzt.market/account/api
LZT_API_KEY = os.getenv("LZT_API_KEY", "YOUR_LZT_API_KEY_HERE")
LZT_BASE_URL = os.getenv("LZT_BASE_URL", "https://prod-api.lzt.market")

# ==================== Product Configuration ====================
# Fixed price user pays (INR)
ACCOUNT_PRICE_INR = float(os.getenv("ACCOUNT_PRICE_INR", "70.0"))
# Max price we're willing to pay on LZT (USD) - safety cap
MAX_LZT_PRICE_USD = float(os.getenv("MAX_LZT_PRICE_USD", "0.15"))
# Country filter for LZT search
ACCOUNT_COUNTRY = os.getenv("ACCOUNT_COUNTRY", "IN")

# ==================== Admin Configuration ====================
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))

# ==================== UPI Payment Details ====================
UPI_ID = os.getenv("UPI_ID", "KaizenSeller@ybl")
UPI_NAME = os.getenv("UPI_NAME", "BHARAT LAL GUPTA")
# UPI QR code image URL or local file path (set to generate auto QR)
UPI_QR_URL = os.getenv("UPI_QR_URL", "")

# ==================== Deposit ====================
MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", "10.0"))

# ==================== Database ====================
DB_PATH = os.getenv("DB_PATH", "bot_database.db")
