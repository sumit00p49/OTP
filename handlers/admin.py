"""
Admin panel.
/admin → Pending, Money, Revenue, Stats, Ban/Unban, Users Dashboard, Broadcast
"""

import logging
from datetime import date
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS
from services.wallet import credit, get_balance
from utils.formatters import format_deposit_approved, format_deposit_rejected
from database import get_db

logger = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_user_id_add = State()
    waiting_amount_add = State()
    waiting_user_id_deduct = State()
    waiting_amount_deduct = State()
    waiting_user_lookup = State()
    waiting_broadcast = State()
    waiting_ban_user = State()



def admin_panel_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📋 Pending Requests", callback_data="admin_pending"))
    b.row(InlineKeyboardButton(text="➕ Add Money", callback_data="admin_add_money"),
          InlineKeyboardButton(text="➖ Deduct Money", callback_data="admin_deduct_money"))
    b.row(InlineKeyboardButton(text="💰 Today Revenue", callback_data="admin_revenue"))
    b.row(InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
          InlineKeyboardButton(text="🔍 User Lookup", callback_data="admin_user_lookup"))
    b.row(InlineKeyboardButton(text="🚫 Ban User", callback_data="admin_ban"),
          InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban"))
    b.row(InlineKeyboardButton(text="👥 Users Dashboard", callback_data="admin_users_dashboard"))
    b.row(InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"))
    return b.as_markup()

def admin_back_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_panel"))
    return b.as_markup()

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Not authorized.")
    await state.clear()
    await message.answer("🔐 <b>𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b>\n━━━━━━━━━━━━━━━━━━━━━",
                         reply_markup=admin_panel_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "admin_panel")
async def admin_panel_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await callback.message.edit_text("🔐 <b>𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b>\n━━━━━━━━━━━━━━━━━━━━━",
                                     reply_markup=admin_panel_keyboard(), parse_mode="HTML")
    await callback.answer()



# ==================== Pending ====================
@router.callback_query(F.data == "admin_pending")
async def admin_pending(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    db = await get_db()
    cur = await db.execute("SELECT d.id,d.user_id,d.amount,d.created_at,u.first_name FROM deposits d LEFT JOIN users u ON d.user_id=u.user_id WHERE d.status='PENDING' ORDER BY d.created_at DESC LIMIT 10")
    rows = await cur.fetchall()
    msg = "📋 <b>Pending</b>\n\n" + ("✅ None!" if not rows else "\n".join(f"#{r[0]} | {r[4]} | ₹{r[2]:.0f}" for r in rows))
    await callback.message.edit_text(msg, reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

# ==================== Add Money ====================
@router.callback_query(F.data == "admin_add_money")
async def admin_add_money(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_user_id_add)
    await callback.message.edit_text("➕ <b>Add Money</b>\n\nSend User ID:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_user_id_add)
async def add_uid(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: uid = int(message.text.strip())
    except: return await message.answer("⚠️ Invalid ID")
    db = await get_db()
    cur = await db.execute("SELECT first_name,wallet_balance FROM users WHERE user_id=?", (uid,))
    row = await cur.fetchone()
    if not row: return await message.answer("❌ Not found")
    await state.update_data(target_user_id=uid, target_name=row[0])
    await state.set_state(AdminStates.waiting_amount_add)
    await message.answer(f"👤 {row[0]} | ₹{row[1]:.2f}\n\nAmount to ADD:", parse_mode="HTML")

@router.message(AdminStates.waiting_amount_add)
async def add_amt(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: amt = float(message.text.strip().replace("₹","").replace(",",""))
    except: return await message.answer("⚠️ Invalid")
    data = await state.get_data()
    new = await credit(data["target_user_id"], amt)
    await state.clear()
    await message.answer(f"✅ +₹{amt:.0f} → Balance: ₹{new:.2f}", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    try: await message.bot.send_message(data["target_user_id"], f"💰 ₹{amt:.0f} added by admin. Balance: ₹{new:.2f}", parse_mode="HTML")
    except: pass



# ==================== Deduct Money ====================
@router.callback_query(F.data == "admin_deduct_money")
async def admin_deduct(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_user_id_deduct)
    await callback.message.edit_text("➖ <b>Deduct Money</b>\n\nSend User ID:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_user_id_deduct)
async def deduct_uid(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: uid = int(message.text.strip())
    except: return await message.answer("⚠️ Invalid ID")
    db = await get_db()
    cur = await db.execute("SELECT first_name,wallet_balance FROM users WHERE user_id=?", (uid,))
    row = await cur.fetchone()
    if not row: return await message.answer("❌ Not found")
    await state.update_data(target_user_id=uid, target_name=row[0])
    await state.set_state(AdminStates.waiting_amount_deduct)
    await message.answer(f"👤 {row[0]} | ₹{row[1]:.2f}\n\nAmount to DEDUCT:", parse_mode="HTML")

@router.message(AdminStates.waiting_amount_deduct)
async def deduct_amt(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: amt = float(message.text.strip().replace("₹","").replace(",",""))
    except: return await message.answer("⚠️ Invalid")
    data = await state.get_data()
    db = await get_db()
    await db.execute("UPDATE users SET wallet_balance=MAX(0,wallet_balance-?) WHERE user_id=?", (amt, data["target_user_id"]))
    await db.commit()
    new = await get_balance(data["target_user_id"])
    await state.clear()
    await message.answer(f"✅ -₹{amt:.0f} → Balance: ₹{new:.2f}", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    try: await message.bot.send_message(data["target_user_id"], f"⚠️ ₹{amt:.0f} deducted. Balance: ₹{new:.2f}", parse_mode="HTML")
    except: pass

# ==================== Revenue ====================
@router.callback_query(F.data == "admin_revenue")
async def admin_revenue(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    db = await get_db()
    today = date.today().isoformat()
    cur = await db.execute("SELECT COUNT(*),COALESCE(SUM(amount),0) FROM deposits WHERE status='APPROVED' AND DATE(created_at)=?", (today,))
    dep = await cur.fetchone()
    cur = await db.execute("SELECT COUNT(*),COALESCE(SUM(amount_paid),0) FROM orders WHERE DATE(created_at)=?", (today,))
    ords = await cur.fetchone()
    await callback.message.edit_text(f"💰 <b>Today ({today})</b>\n━━━━━━━━━━━━━━━━━━━━━\n✅ Deposits: {dep[0]} (₹{dep[1]:.0f})\n🛒 Sales: {ords[0]} (₹{ords[1]:.0f})\n📈 Revenue: ₹{ords[1]:.0f}",
                                     reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

# ==================== Stats ====================
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    db = await get_db()
    users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
    orders = (await (await db.execute("SELECT COUNT(*),COALESCE(SUM(amount_paid),0) FROM orders")).fetchone())
    deps = (await (await db.execute("SELECT COALESCE(SUM(amount),0) FROM deposits WHERE status='APPROVED'")).fetchone())[0]
    await callback.message.edit_text(f"📊 <b>Stats</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 Users: {users}\n🛒 Orders: {orders[0]} (₹{orders[1]:.0f})\n💰 Total Deposits: ₹{deps:.0f}",
                                     reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()



# ==================== User Lookup ====================
@router.callback_query(F.data == "admin_user_lookup")
async def admin_lookup(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_user_lookup)
    await callback.message.edit_text("🔍 <b>User Lookup</b>\n\nSend User ID:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_user_lookup)
async def lookup_result(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: uid = int(message.text.strip())
    except: return await message.answer("⚠️ Invalid")
    db = await get_db()
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    u = await cur.fetchone()
    if not u: return await message.answer("❌ Not found")
    oc = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,))).fetchone())[0]
    await state.clear()
    await message.answer(f"🔍 <b>{u['first_name']}</b>\n🆔 <code>{uid}</code>\n💳 ₹{u['wallet_balance']:.2f}\n🛒 Orders: {oc}", reply_markup=admin_back_keyboard(), parse_mode="HTML")

# ==================== Broadcast ====================
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.edit_text("📢 <b>Broadcast</b>\n\nSend your message:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_broadcast)
async def broadcast_send(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    text = message.text or ""
    if not text: return
    await state.clear()
    db = await get_db()
    cur = await db.execute("SELECT user_id FROM users")
    users = await cur.fetchall()
    sent = 0
    for r in users:
        try:
            await message.bot.send_message(r[0], f"📢 {text}", parse_mode="HTML")
            sent += 1
        except: pass
    await message.answer(f"📢 Sent to {sent}/{len(users)} users", reply_markup=admin_back_keyboard(), parse_mode="HTML")


