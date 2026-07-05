"""
Handlers for WhatsApp number service commands (Server 2).
Commands: /wp2_countries, /wp2_price, /wp2_order, /wp2_status, /wp2_cancel
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode

from api_client import api, APIError
from utils.formatter import (
    format_countries,
    format_price,
    format_order,
    format_status,
    format_cancel,
    format_error,
    format_usage,
)

SERVICE_NAME = "WhatsApp (Server 2)"


async def wp2_countries_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp2_countries - list available WhatsApp countries (Server 2)."""
    try:
        data = await api.wp2_countries()
        msg = format_countries(data, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to get countries: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def wp2_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp2_price [country_code] - get price for a country (Server 2)."""
    if not context.args:
        msg = format_usage(
            "/wp2_price",
            "/wp2_price [country_code]",
            "/wp2_price IN",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    country = context.args[0].upper()

    try:
        data = await api.wp2_price(country)
        msg = format_price(data, country, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to get price for {country}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def wp2_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp2_order [country_code] - order a WhatsApp number (Server 2)."""
    if not context.args:
        msg = format_usage(
            "/wp2_order",
            "/wp2_order [country_code]",
            "/wp2_order IN",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    country = context.args[0].upper()

    await update.message.reply_text(
        f"⏳ Ordering {SERVICE_NAME} number for <code>{country}</code>...",
        parse_mode=ParseMode.HTML,
    )

    try:
        data = await api.wp2_order(country)
        msg = format_order(data, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to order number for {country}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def wp2_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp2_status [order_id] - check OTP status (Server 2)."""
    if not context.args:
        msg = format_usage(
            "/wp2_status",
            "/wp2_status [order_id]",
            "/wp2_status 123456",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    order_id = context.args[0]

    try:
        data = await api.wp2_status(order_id)
        msg = format_status(data, order_id, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to check status for order {order_id}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def wp2_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp2_cancel [order_id] - cancel order and get refund (Server 2)."""
    if not context.args:
        msg = format_usage(
            "/wp2_cancel",
            "/wp2_cancel [order_id]",
            "/wp2_cancel 123456",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    order_id = context.args[0]

    try:
        data = await api.wp2_cancel(order_id)
        msg = format_cancel(data, order_id, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to cancel order {order_id}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# Export handlers
wp2_countries_handler = CommandHandler("wp2_countries", wp2_countries_command)
wp2_price_handler = CommandHandler("wp2_price", wp2_price_command)
wp2_order_handler = CommandHandler("wp2_order", wp2_order_command)
wp2_status_handler = CommandHandler("wp2_status", wp2_status_command)
wp2_cancel_handler = CommandHandler("wp2_cancel", wp2_cancel_command)
