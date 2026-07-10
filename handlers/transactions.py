"""
Transaction History + User Dashboard handler.
Shows all deposits + purchases in one unified view.
"""

import json
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.inline import back_to_main_keyboard
from services.wallet import get_balance
from database import get_db

router = Router()


@router.callback_query(F.data == "my_dashboard")
async def user_dashboard(callback: CallbackQuery):
    """Show user dashboard with stats."""
    uid = callback.from_user.id
    db = await get_db()

    balance = await get_balance(uid)

    # Total spent
    cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(amount_paid),0) FROM orders WHERE user_id=?", (uid,))
    orders = await cur.fetchone()

    # Total deposited
    cur = await db.execute("SELECT COALESCE(SUM(amount),0) FROM deposits WHERE user_id=? AND status='APPROVED'", (uid,))
    deposited = (await cur.fetchone())[0]

    # Referral count
    cur = await db.execute("SELECT referral_count FROM users WHERE user_id=?", (uid,))
    ref_count = (await cur.fetchone())[0] or 0

    # Member since
    cur = await db.execute("SELECT created_at FROM users WHERE user_id=?", (uid,))
    joined = (await cur.fetchone())[0] or "N/A"

    msg = (
        "📊 <b>My Dashboard</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>Balance:</b> ₹{balance:.2f}\n"
        f"🛒 <b>Purchases:</b> {orders[0]} accounts\n"
        f"💵 <b>Total Spent:</b> ₹{orders[1]:.0f}\n"
        f"💰 <b>Total Deposited:</b> ₹{deposited:.0f}\n"
        f"👥 <b>Referrals:</b> {ref_count}\n"
        f"📅 <b>Member Since:</b> {str(joined)[:10]}\n"
    )

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📜 Transaction History", callback_data="txn_history:0"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="back_main"))
    await callback.message.edit_text(msg, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("txn_history:"))
async def transaction_history(callback: CallbackQuery):
    """Show unified transaction history (deposits + purchases)."""
    page = int(callback.data.split(":")[1])
    uid = callback.from_user.id
    db = await get_db()
    per_page = 8

    # Get deposits
    cur = await db.execute(
        "SELECT 'deposit' as type, amount, status, created_at FROM deposits WHERE user_id=? "
        "UNION ALL "
        "SELECT 'purchase' as type, amount_paid, 'COMPLETED', created_at FROM orders WHERE user_id=? "
        "ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (uid, uid, per_page, page * per_page),
    )
    rows = await cur.fetchall()

    if not rows:
        if page == 0:
            await callback.message.edit_text(
                "📜 <b>Transaction History</b>\n\n📭 No transactions yet.",
                reply_markup=back_to_main_keyboard(), parse_mode="HTML",
            )
        else:
            await callback.answer("No more transactions", show_alert=True)
        await callback.answer()
        return

    msg = "📜 <b>Transaction History</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    for r in rows:
        txn_type = r[0]
        amount = r[1]
        status = r[2]
        date = str(r[3])[:16]
        if txn_type == "deposit":
            icon = "✅" if status == "APPROVED" else ("⏳" if status == "PENDING" else "❌")
            msg += f"{icon} +₹{amount:.0f} Deposit ({status}) — {date}\n"
        else:
            msg += f"🛒 -₹{amount:.0f} Purchase — {date}\n"

    b = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"txn_history:{page-1}"))
    if len(rows) == per_page:
        nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"txn_history:{page+1}"))
    if nav:
        b.row(*nav)
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="my_dashboard"))
    await callback.message.edit_text(msg, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()
