"""
Admin handlers - approve/reject deposit callbacks.
Only admins (by ID) can trigger these actions.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ADMIN_IDS
from services.wallet import credit
from utils.formatters import format_deposit_approved, format_deposit_rejected
from database import get_db

router = Router()


@router.callback_query(F.data.startswith("admin_approve:"))
async def admin_approve_deposit(callback: CallbackQuery):
    """Admin approves a deposit - credit user wallet."""
    # Security check
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ You are not authorized!", show_alert=True)
        return

    # Parse callback data: admin_approve:deposit_id:user_id:amount
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("❌ Invalid data", show_alert=True)
        return

    deposit_id = int(parts[1])
    user_id = int(parts[2])
    amount = float(parts[3])

    # Update deposit status
    db = await get_db()
    await db.execute(
        """UPDATE deposits SET status = 'APPROVED', admin_id = ?
           WHERE id = ? AND status = 'PENDING'""",
        (callback.from_user.id, deposit_id),
    )
    await db.commit()

    # Credit user wallet
    new_balance = await credit(user_id, amount)

    # Notify user
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=format_deposit_approved(amount, new_balance),
            parse_mode="HTML",
        )
    except Exception:
        pass  # User may have blocked the bot

    # Update admin message
    await callback.message.edit_caption(
        caption=(
            f"{callback.message.caption}\n\n"
            f"✅ <b>APPROVED</b> by {callback.from_user.first_name}\n"
            f"💰 Credited: ₹{amount:.2f}"
        ),
        parse_mode="HTML",
    )
    await callback.answer(f"✅ Approved ₹{amount:.2f} for user {user_id}", show_alert=True)



@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject_deposit(callback: CallbackQuery):
    """Admin rejects a deposit."""
    # Security check
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ You are not authorized!", show_alert=True)
        return

    # Parse callback data: admin_reject:deposit_id:user_id
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Invalid data", show_alert=True)
        return

    deposit_id = int(parts[1])
    user_id = int(parts[2])

    # Update deposit status
    db = await get_db()
    await db.execute(
        """UPDATE deposits SET status = 'REJECTED', admin_id = ?
           WHERE id = ? AND status = 'PENDING'""",
        (callback.from_user.id, deposit_id),
    )
    await db.commit()

    # Notify user
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=format_deposit_rejected(),
            parse_mode="HTML",
        )
    except Exception:
        pass  # User may have blocked the bot

    # Update admin message
    await callback.message.edit_caption(
        caption=(
            f"{callback.message.caption}\n\n"
            f"❌ <b>REJECTED</b> by {callback.from_user.first_name}"
        ),
        parse_mode="HTML",
    )
    await callback.answer(f"❌ Rejected deposit #{deposit_id}", show_alert=True)
