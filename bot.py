"""
Main entry point for the Telegram Shop Bot.
Registers all routers, middleware, and handles startup/shutdown.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database import init_db, close_db
from middlewares.user_middleware import UserRegistrationMiddleware
from services.lzt_api import lzt_api

# Import routers
from handlers.start import router as start_router
from handlers.deposit import router as deposit_router
from handlers.admin import router as admin_router
from handlers.shop import router as shop_router
from handlers.orders import router as orders_router
from handlers.balance import router as balance_router
from handlers.support import router as support_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Startup hook - initialize database."""
    logger.info("Starting bot...")
    await init_db()
    logger.info("Database initialized.")
    me = await bot.get_me()
    logger.info(f"Bot started: @{me.username}")


async def on_shutdown(bot: Bot):
    """Shutdown hook - cleanup."""
    logger.info("Shutting down...")
    await lzt_api.close()
    await close_db()
    logger.info("Cleanup complete.")


async def main():
    """Main function - create bot, register handlers, start polling."""
    # Validate token
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN not set! Edit .env file.")
        sys.exit(1)

    # Create bot with HTML parse mode
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Create dispatcher
    dp = Dispatcher()

    # Register middleware
    dp.message.middleware(UserRegistrationMiddleware())
    dp.callback_query.middleware(UserRegistrationMiddleware())

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Register routers (order matters for handler priority)
    dp.include_router(start_router)
    dp.include_router(deposit_router)
    dp.include_router(admin_router)
    dp.include_router(shop_router)
    dp.include_router(orders_router)
    dp.include_router(balance_router)
    dp.include_router(support_router)

    # Start polling
    logger.info("Bot is running! Press Ctrl+C to stop.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
