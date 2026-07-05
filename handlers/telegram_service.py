"""
Handlers for Telegram number service commands.
Commands: /tg_countries, /tg_price, /tg_order, /tg_code
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode

from api_client import api, APIError
from utils.formatter import (
    format_countries,
    format_price,
    format_order,
    format_otp_code,
    format_error,
    format_usage,
)

SERVICE_NAME = "Telegram"


async def tg_countries_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tg_countries - list available Telegram countries."""
    try:
        data = await api.tg_countries()
        msg = format_countries(data, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to get countries: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def tg_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tg_price [country_code] - get price for a country."""
    if not context.args:
        msg = format_usage(
            "/tg_price",
            "/tg_price [country_code]",
            "/tg_price US",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    country = context.args[0].upper()

    try:
        data = await api.tg_price(country)
        msg = format_price(data, country, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to get price for {country}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def tg_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tg_order [country_code] - order a Telegram number."""
    if not context.args:
        msg = format_usage(
            "/tg_order",
            "/tg_order [country_code]",
            "/tg_order US",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    country = context.args[0].upper()

    await update.message.reply_text(
        f"⏳ Ordering {SERVICE_NAME} number for <code>{country}</code>...",
        parse_mode=ParseMode.HTML,
    )

    try:
        data = await api.tg_order(country)
        msg = format_order(data, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to order number for {country}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def tg_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tg_code [phone_number] - get OTP code for ordered number."""
    if not context.args:
        msg = format_usage(
            "/tg_code",
            "/tg_code [phone_number]",
            "/tg_code 14155551234",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    number = context.args[0]

    try:
        data = await api.tg_code(number)
        msg = format_otp_code(data, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to get code for {number}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# Export handlers
tg_countries_handler = CommandHandler("tg_countries", tg_countries_command)
tg_price_handler = CommandHandler("tg_price", tg_price_command)
tg_order_handler = CommandHandler("tg_order", tg_order_command)
tg_code_handler = CommandHandler("tg_code", tg_code_command)
