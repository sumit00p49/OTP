"""
Admin panel - full admin dashboard with /admin command.
Features: Pending Requests, Add/Deduct Money, Today Revenue, Stats, User Lookup, Broadcast.
Only accessible by ADMIN_IDS.
"""

import logging
from datetime import datetime, date
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from services.wallet import credit, get_balance
from utils.formatters import format_deposit_approved, format_deposit_rejected
from database import get_db

logger = logging.getLogger(__name__)
router = Router()


# ==================== Admin FSM States ====================

class AdminStates(StatesGroup):
    waiting_user_id_add = State()      # Waiting for user ID to add money
    waiting_amount_add = State()       # Waiting for amount to add
    waiting_user_id_deduct = State()   # Waiting for user ID to deduct
    waiting_amount_deduct = State()    # Waiting for amount to deduct
    waiting_user_lookup = State()      # Waiting for user ID to lookup
    waiting_broadcast = State()        # Waiting for broadcast message


# ==================== Admin Keyboards ====================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Main admin panel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Pending Requests", callback_data="admin_pending")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Add Money", callback_data="admin_add_money"),
        InlineKeyboardButton(text="➖ Deduct Money", callback_data="admin_deduct_money"),
    )
    builder.row(
        InlineKeyboardButton(text="💰 Today Revenue", callback_data="admin_revenue")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
        InlineKeyboardButton(text="🔍 User Lookup", callback_data="admin_user_lookup"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
    )
    return builder.as_markup()


def admin_back_keyboard() -> InlineKeyboardMarkup:
    """Back to admin panel."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_panel")
    )
    return builder.as_markup()


# ==================== /admin Command ====================

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Show admin panel."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ You are not authorized.")
        return

    await state.clear()
    await message.answer(
        "🔐 <b>𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select an option below:",
        reply_markup=admin_panel_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_panel")
async def admin_panel_cb(callback: CallbackQuery, state: FSMContext):
    """Return to admin panel."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "🔐 <b>𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select an option below:",
        reply_markup=admin_panel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== Pending Requests ====================

@router.callback_query(F.data == "admin_pending")
async def admin_pending(callback: CallbackQuery):
    """Show pending deposit requests."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return

    db = await get_db()
    cursor = await db.execute(
        """SELECT d.id, d.user_id, d.amount, d.created_at, u.first_name, u.username
           FROM deposits d
           LEFT JOIN users u ON d.user_id = u.user_id
           WHERE d.status = 'PENDING'
           ORDER BY d.created_at DESC LIMIT 10"""
    )
    rows = await cursor.fetchall()

    if not rows:
        await callback.message.edit_text(
            "📋 <b>Pending Requests</b>\n\n"
            "✅ No pending deposits!",
            reply_markup=admin_back_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    msg = f"📋 <b>Pending Requests ({len(rows)})</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    for row in rows:
        name = row[4] or "Unknown"
        username = f"@{row[5]}" if row[5] else "N/A"
        msg += (
            f"🆔 #{row[0]} | {name} ({username})\n"
            f"   💵 ₹{row[2]:.2f} | 🕐 {row[3]}\n\n"
        )
    msg += "💡 Deposits are auto-sent to your DM/group with approve/reject buttons."

    await callback.message.edit_text(
        msg,
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== Add Money ====================

@router.callback_query(F.data == "admin_add_money")
async def admin_add_money(callback: CallbackQuery, state: FSMContext):
    """Start add money flow."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_user_id_add)
    await callback.message.edit_text(
        "➕ <b>Add Money</b>\n\n"
        "Send the <b>User ID</b> (Telegram ID):\n"
        "📌 Example: <code>123456789</code>",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_user_id_add)
async def admin_add_user_id(message: Message, state: FSMContext):
    """Receive user ID for adding money."""
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        user_id = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("⚠️ Invalid User ID. Send a number.")
        return

    # Check user exists
    db = await get_db()
    cursor = await db.execute("SELECT first_name, wallet_balance FROM users WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    if not row:
        await message.answer("❌ User not found in database.")
        return

    await state.update_data(target_user_id=user_id, target_name=row[0], target_balance=row[1])
    await state.set_state(AdminStates.waiting_amount_add)
    await message.answer(
        f"👤 User: <b>{row[0]}</b> (ID: <code>{user_id}</code>)\n"
        f"💳 Current Balance: ₹{row[1]:.2f}\n\n"
        "💵 Enter amount to <b>ADD</b>:",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_amount_add)
async def admin_add_amount(message: Message, state: FSMContext):
    """Add money to user wallet."""
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        amount = float(message.text.strip().replace("₹", "").replace(",", ""))
    except (ValueError, TypeError):
        await message.answer("⚠️ Invalid amount.")
        return

    if amount <= 0:
        await message.answer("⚠️ Amount must be positive.")
        return

    data = await state.get_data()
    user_id = data["target_user_id"]
    new_balance = await credit(user_id, amount)
    await state.clear()

    await message.answer(
        f"✅ <b>Money Added!</b>\n\n"
        f"👤 User: {data['target_name']} (<code>{user_id}</code>)\n"
        f"💵 Added: ₹{amount:.2f}\n"
        f"💳 New Balance: ₹{new_balance:.2f}",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )

    # Notify user
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=f"💰 <b>₹{amount:.2f}</b> has been added to your wallet by admin.\n"
                 f"💳 New Balance: <b>₹{new_balance:.2f}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ==================== Deduct Money ====================

@router.callback_query(F.data == "admin_deduct_money")
async def admin_deduct_money(callback: CallbackQuery, state: FSMContext):
    """Start deduct money flow."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_user_id_deduct)
    await callback.message.edit_text(
        "➖ <b>Deduct Money</b>\n\n"
        "Send the <b>User ID</b> (Telegram ID):\n"
        "📌 Example: <code>123456789</code>",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_user_id_deduct)
async def admin_deduct_user_id(message: Message, state: FSMContext):
    """Receive user ID for deducting money."""
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        user_id = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("⚠️ Invalid User ID.")
        return

    db = await get_db()
    cursor = await db.execute("SELECT first_name, wallet_balance FROM users WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    if not row:
        await message.answer("❌ User not found.")
        return

    await state.update_data(target_user_id=user_id, target_name=row[0], target_balance=row[1])
    await state.set_state(AdminStates.waiting_amount_deduct)
    await message.answer(
        f"👤 User: <b>{row[0]}</b> (ID: <code>{user_id}</code>)\n"
        f"💳 Current Balance: ₹{row[1]:.2f}\n\n"
        "💵 Enter amount to <b>DEDUCT</b>:",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_amount_deduct)
async def admin_deduct_amount(message: Message, state: FSMContext):
    """Deduct money from user wallet."""
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        amount = float(message.text.strip().replace("₹", "").replace(",", ""))
    except (ValueError, TypeError):
        await message.answer("⚠️ Invalid amount.")
        return

    if amount <= 0:
        await message.answer("⚠️ Amount must be positive.")
        return

    data = await state.get_data()
    user_id = data["target_user_id"]

    db = await get_db()
    await db.execute(
        "UPDATE users SET wallet_balance = MAX(0, wallet_balance - ?) WHERE user_id = ?",
        (amount, user_id),
    )
    await db.commit()
    new_balance = await get_balance(user_id)
    await state.clear()

    await message.answer(
        f"✅ <b>Money Deducted!</b>\n\n"
        f"👤 User: {data['target_name']} (<code>{user_id}</code>)\n"
        f"💵 Deducted: ₹{amount:.2f}\n"
        f"💳 New Balance: ₹{new_balance:.2f}",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )

    # Notify user
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=f"⚠️ <b>₹{amount:.2f}</b> has been deducted from your wallet by admin.\n"
                 f"💳 New Balance: <b>₹{new_balance:.2f}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ==================== Today Revenue ====================

@router.callback_query(F.data == "admin_revenue")
async def admin_revenue(callback: CallbackQuery):
    """Show today's revenue."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return

    db = await get_db()
    today = date.today().isoformat()

    # Today's approved deposits
    cursor = await db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM deposits WHERE status = 'APPROVED' AND DATE(created_at) = ?",
        (today,),
    )
    dep_row = await cursor.fetchone()
    dep_count, dep_total = dep_row[0], dep_row[1]

    # Today's orders (sales)
    cursor = await db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount_paid), 0) FROM orders WHERE DATE(created_at) = ?",
        (today,),
    )
    ord_row = await cursor.fetchone()
    ord_count, ord_total = ord_row[0], ord_row[1]

    # Today's pending
    cursor = await db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM deposits WHERE status = 'PENDING' AND DATE(created_at) = ?",
        (today,),
    )
    pend_row = await cursor.fetchone()
    pend_count, pend_total = pend_row[0], pend_row[1]

    await callback.message.edit_text(
        "💰 <b>Today's Revenue</b>\n"
        f"📅 {today}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Deposits Approved:</b> {dep_count} (₹{dep_total:.2f})\n"
        f"🛒 <b>Accounts Sold:</b> {ord_count} (₹{ord_total:.2f})\n"
        f"⏳ <b>Pending Deposits:</b> {pend_count} (₹{pend_total:.2f})\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 <b>Net Revenue:</b> ₹{ord_total:.2f}",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== Stats ====================

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Show overall bot stats."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return

    db = await get_db()

    cursor = await db.execute("SELECT COUNT(*) FROM users")
    total_users = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*), COALESCE(SUM(amount_paid), 0) FROM orders")
    row = await cursor.fetchone()
    total_orders, total_sales = row[0], row[1]

    cursor = await db.execute("SELECT COALESCE(SUM(amount), 0) FROM deposits WHERE status = 'APPROVED'")
    total_deposits = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM deposits WHERE status = 'PENDING'")
    pending_count = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COALESCE(SUM(wallet_balance), 0) FROM users")
    total_wallet = (await cursor.fetchone())[0]

    await callback.message.edit_text(
        "📊 <b>Bot Statistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> {total_users}\n"
        f"🛒 <b>Total Orders:</b> {total_orders}\n"
        f"💵 <b>Total Sales:</b> ₹{total_sales:.2f}\n"
        f"💰 <b>Total Deposits:</b> ₹{total_deposits:.2f}\n"
        f"⏳ <b>Pending Deposits:</b> {pending_count}\n"
        f"💳 <b>Users Wallet Total:</b> ₹{total_wallet:.2f}\n",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== User Lookup ====================

@router.callback_query(F.data == "admin_user_lookup")
async def admin_user_lookup(callback: CallbackQuery, state: FSMContext):
    """Start user lookup flow."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_user_lookup)
    await callback.message.edit_text(
        "🔍 <b>User Lookup</b>\n\n"
        "Send the <b>User ID</b> (Telegram ID):\n"
        "📌 Example: <code>123456789</code>",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_user_lookup)
async def admin_user_lookup_result(message: Message, state: FSMContext):
    """Show user details."""
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        user_id = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("⚠️ Invalid User ID.")
        return

    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    )
    user = await cursor.fetchone()
    if not user:
        await message.answer("❌ User not found.")
        return

    # Get order count
    cursor = await db.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,))
    order_count = (await cursor.fetchone())[0]

    # Get deposit history
    cursor = await db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM deposits WHERE user_id = ? AND status = 'APPROVED'",
        (user_id,),
    )
    dep_row = await cursor.fetchone()

    await state.clear()
    await message.answer(
        f"🔍 <b>User Details</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Name:</b> {user['first_name']}\n"
        f"🆔 <b>ID:</b> <code>{user['user_id']}</code>\n"
        f"📛 <b>Username:</b> @{user['username'] or 'N/A'}\n"
        f"💳 <b>Balance:</b> ₹{user['wallet_balance']:.2f}\n"
        f"🛒 <b>Orders:</b> {order_count}\n"
        f"💰 <b>Total Deposited:</b> ₹{dep_row[1]:.2f} ({dep_row[0]} times)\n"
        f"📅 <b>Joined:</b> {user['created_at']}",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )


# ==================== Broadcast ====================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Start broadcast flow."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.edit_text(
        "📢 <b>Broadcast</b>\n\n"
        "Send the message you want to broadcast to <b>all users</b>.\n\n"
        "⚠️ This will send to everyone. Type your message:",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext):
    """Send broadcast to all users."""
    if message.from_user.id not in ADMIN_IDS:
        return

    broadcast_text = message.text or message.caption or ""
    if not broadcast_text:
        await message.answer("⚠️ Please send a text message.")
        return

    await state.clear()

    db = await get_db()
    cursor = await db.execute("SELECT user_id FROM users")
    users = await cursor.fetchall()

    sent = 0
    failed = 0
    for row in users:
        try:
            await message.bot.send_message(
                chat_id=row[0],
                text=f"📢 <b>Announcement</b>\n\n{broadcast_text}",
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📢 <b>Broadcast Complete!</b>\n\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {sent + failed}",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )


# ==================== Deposit Approve/Reject (kept from before) ====================

@router.callback_query(F.data.startswith("admin_approve:"))
async def admin_approve_deposit(callback: CallbackQuery):
    """Admin approves a deposit."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ You are not authorized!", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("❌ Invalid data", show_alert=True)
        return

    deposit_id = int(parts[1])
    user_id = int(parts[2])
    amount = float(parts[3])

    db = await get_db()
    cursor = await db.execute("SELECT status FROM deposits WHERE id = ?", (deposit_id,))
    row = await cursor.fetchone()
    if row and row[0] != "PENDING":
        await callback.answer(f"⚠️ Already {row[0]}", show_alert=True)
        return

    await db.execute(
        "UPDATE deposits SET status = 'APPROVED', admin_id = ? WHERE id = ? AND status = 'PENDING'",
        (callback.from_user.id, deposit_id),
    )
    await db.commit()

    new_balance = await credit(user_id, amount)
    logger.info("Deposit #%s approved: ₹%.2f to user %s", deposit_id, amount, user_id)

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=format_deposit_approved(amount, new_balance),
            parse_mode="HTML",
        )
    except Exception:
        pass

    try:
        current_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=f"{current_caption}\n\n✅ <b>APPROVED</b> by {callback.from_user.first_name}\n💰 ₹{amount:.2f} | New Bal: ₹{new_balance:.2f}",
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.answer(f"✅ Approved ₹{amount:.2f}", show_alert=True)


@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject_deposit(callback: CallbackQuery):
    """Admin rejects a deposit."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ You are not authorized!", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Invalid data", show_alert=True)
        return

    deposit_id = int(parts[1])
    user_id = int(parts[2])

    db = await get_db()
    cursor = await db.execute("SELECT status FROM deposits WHERE id = ?", (deposit_id,))
    row = await cursor.fetchone()
    if row and row[0] != "PENDING":
        await callback.answer(f"⚠️ Already {row[0]}", show_alert=True)
        return

    await db.execute(
        "UPDATE deposits SET status = 'REJECTED', admin_id = ? WHERE id = ? AND status = 'PENDING'",
        (callback.from_user.id, deposit_id),
    )
    await db.commit()

    try:
        await callback.bot.send_message(
            chat_id=user_id, text=format_deposit_rejected(), parse_mode="HTML",
        )
    except Exception:
        pass

    try:
        current_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=f"{current_caption}\n\n❌ <b>REJECTED</b> by {callback.from_user.first_name}",
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.answer(f"❌ Rejected #{deposit_id}", show_alert=True)
