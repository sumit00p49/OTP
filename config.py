"""
Configuration module for the Telegram OTP Bot.
Loads settings from environment variables or .env file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# OTPNOW API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://otpnowapi.lynkzap.shop")
API_KEY = os.getenv("API_KEY", "tJ8vR1xWp4m2Q9zK5gL6vYd3sB7hN0a")
