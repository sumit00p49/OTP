"""
Handler for balance check.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.inline import balance_keyboard
from utils.formatters import format_balance
from services.wallet import get_balance

router = Router()


@router.callback_query(F.data == "check_balance")
async def check_balance_callback(callback: CallbackQuery):
    """Show current wallet balance."""
    balance = await get_balance(callback.from_user.id)

    await callback.message.edit_text(
        format_balance(balance),
        reply_markup=balance_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
