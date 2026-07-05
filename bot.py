"""
Main entry point for the Telegram OTP Bot.
Registers all command handlers and starts the bot.
"""

import logging
import sys

from telegram import Update
from telegram.ext import Application, ContextTypes
from telegram.constants import ParseMode

from config import BOT_TOKEN
from api_client import api

# Import handlers
from handlers.start import start_handler
from handlers.balance import balance_handler
from handlers.telegram_service import (
    tg_countries_handler,
    tg_price_handler,
    tg_order_handler,
    tg_code_handler,
)
from handlers.whatsapp_service import (
    wp_countries_handler,
    wp_price_handler,
    wp_order_handler,
    wp_status_handler,
    wp_cancel_handler,
)
from handlers.whatsapp2_service import (
    wp2_countries_handler,
    wp2_price_handler,
    wp2_order_handler,
    wp2_status_handler,
    wp2_cancel_handler,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unhandled errors."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # Try to notify the user
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "⚠️ <b>An unexpected error occurred.</b>\n\n"
            "Please try again later or contact support.",
            parse_mode=ParseMode.HTML,
        )


async def post_shutdown(application: Application) -> None:
    """Cleanup on shutdown - close API session."""
    await api.close()
    logger.info("Bot shutdown complete. API session closed.")


def main() -> None:
    """Start the bot."""
    # Validate bot token
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN is not set! Please set it in .env file or environment variable.")
        sys.exit(1)

    logger.info("Starting OTP Now Bot...")

    # Build application
    application = Application.builder().token(BOT_TOKEN).post_shutdown(post_shutdown).build()

    # Register handlers - Start & Balance
    application.add_handler(start_handler)
    application.add_handler(balance_handler)

    # Register handlers - Telegram service
    application.add_handler(tg_countries_handler)
    application.add_handler(tg_price_handler)
    application.add_handler(tg_order_handler)
    application.add_handler(tg_code_handler)

    # Register handlers - WhatsApp Server 1
    application.add_handler(wp_countries_handler)
    application.add_handler(wp_price_handler)
    application.add_handler(wp_order_handler)
    application.add_handler(wp_status_handler)
    application.add_handler(wp_cancel_handler)

    # Register handlers - WhatsApp Server 2
    application.add_handler(wp2_countries_handler)
    application.add_handler(wp2_price_handler)
    application.add_handler(wp2_order_handler)
    application.add_handler(wp2_status_handler)
    application.add_handler(wp2_cancel_handler)

    # Register error handler
    application.add_error_handler(error_handler)

    # Start polling
    logger.info("Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
