"""
Handler for /start command and main menu navigation.
"""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.inline import main_menu_keyboard
from utils.formatters import format_welcome
from services.wallet import get_balance

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - show welcome and main menu."""
    await state.clear()
    user = message.from_user
    balance = await get_balance(user.id)

    await message.answer(
        format_welcome(user.first_name or "User", balance),
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Handle back to main menu."""
    await state.clear()
    user = callback.from_user
    balance = await get_balance(user.id)

    await callback.message.edit_text(
        format_welcome(user.first_name or "User", balance),
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
