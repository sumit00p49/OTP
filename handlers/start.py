"""
Handler for /start command with referral support and force join check.
"""

import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.inline import main_menu_keyboard
from utils.formatters import format_welcome
from services.wallet import get_balance
from services.referral import process_referral, get_referral_count, get_referral_link
from config import FORCE_JOIN_CHANNEL
from database import get_db

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject = None):
    """Handle /start with optional referral param."""
    await state.clear()
    user = message.from_user

    # Check if banned
    db = await get_db()
    cur = await db.execute("SELECT is_banned FROM users WHERE user_id = ?", (user.id,))
    row = await cur.fetchone()
    if row and row[0] == 1:
        await message.answer("⛔ You are banned from this bot.")
        return

    # Handle referral: /start ref_123456789
    if command and command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args.replace("ref_", ""))
            bonus_given = await process_referral(referrer_id, user.id)
            if bonus_given:
                try:
                    await message.bot.send_message(
                        referrer_id,
                        "🎉 <b>Referral Bonus!</b>\n\n"
                        "You got <b>₹10</b> for reaching 5 referrals!\n"
                        "💳 Credited to your wallet.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        except (ValueError, TypeError):
            pass

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


@router.callback_query(F.data == "check_joined")
async def check_joined(callback: CallbackQuery):
    """Verify user joined the channel."""
    if not FORCE_JOIN_CHANNEL:
        await callback.answer("✅ No channel required!", show_alert=True)
        return

    try:
        member = await callback.bot.get_chat_member(
            chat_id=f"@{FORCE_JOIN_CHANNEL}", user_id=callback.from_user.id
        )
        if member.status in ("left", "kicked"):
            await callback.answer("❌ You haven't joined yet! Join and try again.", show_alert=True)
            return
    except Exception:
        pass  # If check fails, let them through

    await callback.answer("✅ Verified! Welcome!", show_alert=True)
    # Show main menu
    balance = await get_balance(callback.from_user.id)
    await callback.message.edit_text(
        format_welcome(callback.from_user.first_name or "User", balance),
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "my_referral")
async def my_referral(callback: CallbackQuery):
    """Show user's referral link and stats."""
    user_id = callback.from_user.id
    count = await get_referral_count(user_id)
    me = await callback.bot.get_me()
    link = get_referral_link(me.username, user_id)

    remaining = 5 - (count % 5)
    msg = (
        "🎟️ <b>Referral Program</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Your Referrals: <b>{count}</b>\n"
        f"🎯 Next Bonus: <b>{remaining} more</b> needed\n"
        f"💰 Bonus: <b>₹10</b> per 5 referrals\n\n"
        f"🔗 Your Link:\n<code>{link}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Share this link. When 5 people join,\n"
        "you get ₹10 in your wallet!"
    )

    from keyboards.inline import back_to_main_keyboard
    await callback.message.edit_text(msg, reply_markup=back_to_main_keyboard(), parse_mode="HTML")
    await callback.answer()
