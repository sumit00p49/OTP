"""
Handler for /start command.
Shows welcome message with all available commands.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode

from utils.formatter import format_welcome


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command - show welcome message."""
    await update.message.reply_text(
        format_welcome(),
        parse_mode=ParseMode.HTML,
    )


# Export handler
start_handler = CommandHandler("start", start_command)
