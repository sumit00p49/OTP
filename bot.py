"""
Main entry point for the Telegram Shop Bot.
Registers all routers, middleware, scheduler, and handles startup/shutdown.
"""

import asyncio
import logging
import sys
from datetime import datetime, time

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, DAILY_REPORT_HOUR
from database import init_db, close_db
from middlewares.user_middleware import UserRegistrationMiddleware
from middlewares.force_join import ForceJoinMiddleware
from services.lzt_api import lzt_api
from services.daily_report import send_daily_report

# Import routers
from handlers.start import router as start_router
from handlers.deposit import router as deposit_router
from handlers.admin import router as admin_router
from handlers.shop import router as shop_router
from handlers.orders import router as orders_router
from handlers.balance import router as balance_router
from handlers.support import router as support_router
from handlers.transactions import router as transactions_router
from handlers.rating import router as rating_router
from handlers.preview import router as preview_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def daily_report_scheduler(bot: Bot):
    """Background task: send daily report to admins."""
    while True:
        now = datetime.now()
        # Calculate seconds until next report time
        target = now.replace(hour=DAILY_REPORT_HOUR, minute=0, second=0)
        if now >= target:
            # Already past today's time, schedule for tomorrow
            target = target.replace(day=now.day + 1)
        wait_seconds = (target - now).total_seconds()
        logger.info("Daily report scheduled in %.0f seconds", wait_seconds)
        await asyncio.sleep(wait_seconds)
        try:
            await send_daily_report(bot)
            logger.info("Daily report sent!")
        except Exception as e:
            logger.error("Daily report failed: %s", e)
        # Wait a bit to avoid double-send
        await asyncio.sleep(60)


async def on_startup(bot: Bot):
    """Startup hook - initialize database and verify APIs."""
    logger.info("Starting bot...")
    await init_db()
    logger.info("Database initialized.")

    # Best-effort LZT API key verification
    try:
        balance = await lzt_api.get_seller_balance()
        if balance is not None:
            logger.info(f"LZT API connected. Seller balance: ${balance}")
        else:
            logger.warning("LZT API: balance unavailable. Check key.")
    except Exception as e:
        logger.warning(f"LZT API check failed: {e}")

    me = await bot.get_me()
    logger.info(f"Bot started: @{me.username}")

    # Start daily report scheduler
    asyncio.create_task(daily_report_scheduler(bot))


async def on_shutdown(bot: Bot):
    """Shutdown hook - cleanup."""
    logger.info("Shutting down...")
    await lzt_api.close()
    await close_db()
    logger.info("Cleanup complete.")


async def main():
    """Main function."""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN not set!")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Register middleware (order: force join first, then user registration)
    dp.message.middleware(ForceJoinMiddleware())
    dp.callback_query.middleware(ForceJoinMiddleware())
    dp.message.middleware(UserRegistrationMiddleware())
    dp.callback_query.middleware(UserRegistrationMiddleware())

    # Startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Register routers
    dp.include_router(start_router)
    dp.include_router(deposit_router)
    dp.include_router(admin_router)
    dp.include_router(shop_router)
    dp.include_router(orders_router)
    dp.include_router(balance_router)
    dp.include_router(support_router)
    dp.include_router(transactions_router)
    dp.include_router(rating_router)
    dp.include_router(preview_router)

    logger.info("Bot is running! Press Ctrl+C to stop.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
