"""
Language selection handler.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.language import set_user_lang, get_user_lang
from keyboards.inline import back_to_main_keyboard

router = Router()


@router.callback_query(F.data == "change_lang")
async def language_menu(callback: CallbackQuery):
    """Show language selection."""
    current = await get_user_lang(callback.from_user.id)
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text=f"{'✅' if current == 'en' else '⬜'} 🇬🇧 English",
            callback_data="set_lang:en",
        ),
        InlineKeyboardButton(
            text=f"{'✅' if current == 'hi' else '⬜'} 🇮🇳 हिन्दी",
            callback_data="set_lang:hi",
        ),
    )
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="back_main"))

    await callback.message.edit_text(
        "🌐 <b>Select Language</b>\n\n"
        "Choose your preferred language:",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_lang:"))
async def set_language(callback: CallbackQuery):
    """Set user language."""
    lang = callback.data.split(":")[1]
    await set_user_lang(callback.from_user.id, lang)
    name = "English 🇬🇧" if lang == "en" else "हिन्दी 🇮🇳"
    await callback.answer(f"✅ Language set to {name}", show_alert=True)

    # Redirect to main menu
    from services.wallet import get_balance
    from utils.formatters import format_welcome
    from keyboards.inline import main_menu_keyboard
    balance = await get_balance(callback.from_user.id)
    await callback.message.edit_text(
        format_welcome(callback.from_user.first_name or "User", balance),
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
