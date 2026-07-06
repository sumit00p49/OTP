"""
Configuration module for the Telegram Shop Bot.
Loads all settings from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# LZT Market API
LZT_API_KEY = os.getenv("LZT_API_KEY", "YOUR_LZT_API_KEY_HERE")
LZT_BASE_URL = os.getenv("LZT_BASE_URL", "https://api.lzt.market")

# Admin Configuration
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))

# UPI Payment Details
UPI_ID = os.getenv("UPI_ID", "KaizenSeller@ybl")
UPI_NAME = os.getenv("UPI_NAME", "Kaizen Seller")

# Pricing Configuration (INR)
CHEAP_ACC_PRICE = float(os.getenv("CHEAP_ACC_PRICE", "30.0"))
GOOD_ACC_PRICE = float(os.getenv("GOOD_ACC_PRICE", "60.0"))

# Minimum deposit amount
MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", "10.0"))

# Database
DB_PATH = os.getenv("DB_PATH", "bot_database.db")

# LZT Category for Telegram accounts
LZT_CATEGORY = os.getenv("LZT_CATEGORY", "telegram")
