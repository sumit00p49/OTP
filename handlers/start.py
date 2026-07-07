"""
Handler for /start command and main menu navigation.
Uses Telegram Premium custom emojis for premium look.
"""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, MessageEntity
from aiogram.fsm.context import FSMContext

from keyboards.inline import main_menu_keyboard
from utils.formatters import format_welcome_text, build_welcome_entities
from services.wallet import get_balance

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - show welcome with premium custom emojis."""
    await state.clear()
    user = message.from_user
    balance = await get_balance(user.id)

    text, entities = build_welcome_entities(user.first_name or "User", balance)

    await message.answer(
        text=text,
        entities=entities,
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Handle back to main menu with custom emojis."""
    await state.clear()
    user = callback.from_user
    balance = await get_balance(user.id)

    text, entities = build_welcome_entities(user.first_name or "User", balance)

    await callback.message.edit_text(
        text=text,
        entities=entities,
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
