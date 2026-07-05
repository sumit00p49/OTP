"""
Handlers for WhatsApp number service commands (Server 1).
Commands: /wp_countries, /wp_price, /wp_order, /wp_status, /wp_cancel
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

SERVICE_NAME = "WhatsApp (Server 1)"


async def wp_countries_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp_countries - list available WhatsApp countries (Server 1)."""
    try:
        data = await api.wp_countries()
        msg = format_countries(data, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to get countries: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def wp_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp_price [country_code] - get price for a country (Server 1)."""
    if not context.args:
        msg = format_usage(
            "/wp_price",
            "/wp_price [country_code]",
            "/wp_price IN",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    country = context.args[0].upper()

    try:
        data = await api.wp_price(country)
        msg = format_price(data, country, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to get price for {country}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def wp_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp_order [country_code] - order a WhatsApp number (Server 1)."""
    if not context.args:
        msg = format_usage(
            "/wp_order",
            "/wp_order [country_code]",
            "/wp_order IN",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    country = context.args[0].upper()

    await update.message.reply_text(
        f"⏳ Ordering {SERVICE_NAME} number for <code>{country}</code>...",
        parse_mode=ParseMode.HTML,
    )

    try:
        data = await api.wp_order(country)
        msg = format_order(data, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to order number for {country}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def wp_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp_status [order_id] - check OTP status (Server 1)."""
    if not context.args:
        msg = format_usage(
            "/wp_status",
            "/wp_status [order_id]",
            "/wp_status 123456",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    order_id = context.args[0]

    try:
        data = await api.wp_status(order_id)
        msg = format_status(data, order_id, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to check status for order {order_id}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def wp_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wp_cancel [order_id] - cancel order and get refund (Server 1)."""
    if not context.args:
        msg = format_usage(
            "/wp_cancel",
            "/wp_cancel [order_id]",
            "/wp_cancel 123456",
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    order_id = context.args[0]

    try:
        data = await api.wp_cancel(order_id)
        msg = format_cancel(data, order_id, SERVICE_NAME)
    except APIError as e:
        msg = format_error(f"Failed to cancel order {order_id}: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# Export handlers
wp_countries_handler = CommandHandler("wp_countries", wp_countries_command)
wp_price_handler = CommandHandler("wp_price", wp_price_command)
wp_order_handler = CommandHandler("wp_order", wp_order_command)
wp_status_handler = CommandHandler("wp_status", wp_status_command)
wp_cancel_handler = CommandHandler("wp_cancel", wp_cancel_command)
