"""
Admin handlers - approve/reject deposit callbacks.
Only users with IDs in ADMIN_IDS can trigger these.

Handles both:
- Photo messages (caption editing)
- Document messages (caption editing)
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ADMIN_IDS
from services.wallet import credit
from utils.formatters import format_deposit_approved, format_deposit_rejected
from database import get_db

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("admin_approve:"))
async def admin_approve_deposit(callback: CallbackQuery):
    """Admin approves a deposit - credit user wallet."""
    # Security check
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ You are not authorized!", show_alert=True)
        return

    # Parse: admin_approve:deposit_id:user_id:amount
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("❌ Invalid data", show_alert=True)
        return

    deposit_id = int(parts[1])
    user_id = int(parts[2])
    amount = float(parts[3])

    # Check if already processed
    db = await get_db()
    cursor = await db.execute(
        "SELECT status FROM deposits WHERE id = ?", (deposit_id,)
    )
    row = await cursor.fetchone()
    if row and row[0] != "PENDING":
        await callback.answer(f"⚠️ Already {row[0]}", show_alert=True)
        return

    # Update deposit status
    await db.execute(
        """UPDATE deposits SET status = 'APPROVED', admin_id = ?
           WHERE id = ? AND status = 'PENDING'""",
        (callback.from_user.id, deposit_id),
    )
    await db.commit()

    # Credit user wallet
    new_balance = await credit(user_id, amount)
    logger.info("Deposit #%s approved: ₹%.2f to user %s (new bal: %.2f)",
                deposit_id, amount, user_id, new_balance)

    # Notify user
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=format_deposit_approved(amount, new_balance),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Could not notify user %s: %s", user_id, e)

    # Update admin message (works for both photo and document captions)
    try:
        current_caption = callback.message.caption or ""
        new_caption = (
            f"{current_caption}\n\n"
            f"✅ <b>APPROVED</b> by {callback.from_user.first_name}\n"
            f"💰 Credited: ₹{amount:.2f}\n"
            f"💳 New Balance: ₹{new_balance:.2f}"
        )
        await callback.message.edit_caption(
            caption=new_caption,
            parse_mode="HTML",
            reply_markup=None,  # Remove buttons after action
        )
    except Exception as e:
        logger.warning("Could not edit admin message: %s", e)

    await callback.answer(f"✅ Approved ₹{amount:.2f} for user {user_id}", show_alert=True)


@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject_deposit(callback: CallbackQuery):
    """Admin rejects a deposit."""
    # Security check
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ You are not authorized!", show_alert=True)
        return

    # Parse: admin_reject:deposit_id:user_id
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Invalid data", show_alert=True)
        return

    deposit_id = int(parts[1])
    user_id = int(parts[2])

    # Check if already processed
    db = await get_db()
    cursor = await db.execute(
        "SELECT status FROM deposits WHERE id = ?", (deposit_id,)
    )
    row = await cursor.fetchone()
    if row and row[0] != "PENDING":
        await callback.answer(f"⚠️ Already {row[0]}", show_alert=True)
        return

    # Update status
    await db.execute(
        """UPDATE deposits SET status = 'REJECTED', admin_id = ?
           WHERE id = ? AND status = 'PENDING'""",
        (callback.from_user.id, deposit_id),
    )
    await db.commit()
    logger.info("Deposit #%s rejected by admin %s", deposit_id, callback.from_user.id)

    # Notify user
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=format_deposit_rejected(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Could not notify user %s: %s", user_id, e)

    # Update admin message
    try:
        current_caption = callback.message.caption or ""
        new_caption = (
            f"{current_caption}\n\n"
            f"❌ <b>REJECTED</b> by {callback.from_user.first_name}"
        )
        await callback.message.edit_caption(
            caption=new_caption,
            parse_mode="HTML",
            reply_markup=None,  # Remove buttons
        )
    except Exception as e:
        logger.warning("Could not edit admin message: %s", e)

    await callback.answer(f"❌ Rejected deposit #{deposit_id}", show_alert=True)
