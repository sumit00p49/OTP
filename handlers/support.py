"""
Handler for support.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.inline import support_keyboard
from utils.formatters import format_support

router = Router()


@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery):
    """Show support information."""
    await callback.message.edit_text(
        format_support(),
        reply_markup=support_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
