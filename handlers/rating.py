"""
Account Rating system.
After purchase, user can rate 👍/👎. Stored in orders table.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_db
from keyboards.inline import back_to_main_keyboard

router = Router()


@router.callback_query(F.data.startswith("rate:"))
async def rate_account(callback: CallbackQuery):
    """User rates an account (👍 or 👎)."""
    parts = callback.data.split(":")
    if len(parts) != 3:
        return await callback.answer("❌ Invalid", show_alert=True)

    order_id = parts[1]
    rating = parts[2]  # "good" or "bad"

    db = await get_db()

    # Check if order exists and belongs to user
    cur = await db.execute(
        "SELECT user_id FROM orders WHERE order_id = ?", (order_id,)
    )
    row = await cur.fetchone()
    if not row or row[0] != callback.from_user.id:
        return await callback.answer("❌ Order not found", show_alert=True)

    # Save rating (add rating column if needed)
    try:
        await db.execute("ALTER TABLE orders ADD COLUMN rating TEXT DEFAULT ''")
    except Exception:
        pass

    await db.execute(
        "UPDATE orders SET rating = ? WHERE order_id = ?",
        (rating, order_id),
    )
    await db.commit()

    emoji = "👍" if rating == "good" else "👎"
    await callback.answer(f"{emoji} Thank you for your feedback!", show_alert=True)

    # Update message to show rated
    try:
        text = callback.message.text or callback.message.caption or ""
        await callback.message.edit_text(
            text + f"\n\n{emoji} <b>Rated: {'Good' if rating == 'good' else 'Bad'}</b>",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        pass
