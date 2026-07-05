"""
Handler for /balance command.
Checks and displays the current account balance.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode

from api_client import api, APIError
from utils.formatter import format_balance, format_error


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /balance command - check account balance."""
    try:
        data = await api.check_balance()
        msg = format_balance(data)
    except APIError as e:
        msg = format_error(f"Failed to check balance: {e.message}")
    except Exception as e:
        msg = format_error(f"Unexpected error: {str(e)}")

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# Export handler
balance_handler = CommandHandler("balance", balance_command)
