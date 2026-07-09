"""
Admin panel with Product Manager.
/admin → Pending, Money, Revenue, Stats, Products, Broadcast
Product Manager → Add/Remove/Price countries via inline buttons (no .env editing!)
All filters auto-include nsb=1 for OTP support.
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
from services.product_manager import (
    get_all_products, get_product, add_product,
    remove_product, update_product_price, update_product_filters,
)
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
    waiting_product_code = State()
    waiting_product_name = State()
    waiting_product_flag = State()
    waiting_product_price = State()
    waiting_product_max_lzt = State()
    waiting_product_origin = State()
    waiting_price_update = State()



def admin_panel_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📋 Pending Requests", callback_data="admin_pending"))
    b.row(InlineKeyboardButton(text="➕ Add Money", callback_data="admin_add_money"),
          InlineKeyboardButton(text="➖ Deduct Money", callback_data="admin_deduct_money"))
    b.row(InlineKeyboardButton(text="💰 Today Revenue", callback_data="admin_revenue"))
    b.row(InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
          InlineKeyboardButton(text="🔍 User Lookup", callback_data="admin_user_lookup"))
    b.row(InlineKeyboardButton(text="🛒 Product Manager", callback_data="admin_products"))
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



# ==================== PRODUCT MANAGER ====================

@router.callback_query(F.data == "admin_products")
async def admin_products(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.clear()
    products = get_all_products()
    msg = "🛒 <b>Product Manager</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    for p in products:
        f_str = ", ".join(f"{k}={v}" for k,v in p.get("filters",{}).items())
        msg += f"{p['flag']} <b>{p['name']}</b> ({p['code']}) — ₹{p['price']:.0f}\n   🔧 {f_str}\n\n"
    if not products:
        msg += "📭 No products.\n"
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➕ Add Country", callback_data="prod_add"))
    if products:
        b.row(InlineKeyboardButton(text="🗑️ Remove Country", callback_data="prod_remove"))
        b.row(InlineKeyboardButton(text="💵 Change Price", callback_data="prod_price"))
        b.row(InlineKeyboardButton(text="🔧 Edit Filters", callback_data="prod_filters"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_panel"))
    await callback.message.edit_text(msg, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()

# ---- Add Country ----
@router.callback_query(F.data == "prod_add")
async def prod_add(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_product_code)
    await callback.message.edit_text("➕ <b>Add Country</b>\n\nSend 2-letter code:\n📌 <code>US</code> <code>BD</code> <code>ID</code> <code>MM</code>", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_product_code)
async def prod_code(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    code = message.text.strip().upper()[:2]
    if len(code) != 2 or not code.isalpha():
        return await message.answer("⚠️ Send 2 letters (e.g. US)")
    if get_product(code):
        return await message.answer(f"⚠️ {code} already exists!")
    await state.update_data(new_code=code)
    await state.set_state(AdminStates.waiting_product_name)
    await message.answer(f"✅ Code: {code}\n\nSend country name:", parse_mode="HTML")

@router.message(AdminStates.waiting_product_name)
async def prod_name(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.update_data(new_name=message.text.strip()[:30])
    await state.set_state(AdminStates.waiting_product_flag)
    await message.answer("✅ Now send flag emoji:\n📌 🇺🇸 🇧🇩 🇮🇩 🇲🇲 🇻🇳")

@router.message(AdminStates.waiting_product_flag)
async def prod_flag(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.update_data(new_flag=message.text.strip()[:4])
    await state.set_state(AdminStates.waiting_product_price)
    await message.answer("✅ Now send <b>price in INR</b> (user pays):\n📌 Example: <code>70</code>", parse_mode="HTML")

@router.message(AdminStates.waiting_product_price)
async def prod_price_input(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: price = float(message.text.strip().replace("₹",""))
    except: return await message.answer("⚠️ Invalid number")
    await state.update_data(new_price=price)
    await state.set_state(AdminStates.waiting_product_max_lzt)
    await message.answer(f"✅ Price: ₹{price:.0f}\n\nSend <b>max USD</b> to pay on LZT:\n📌 Example: <code>0.15</code>", parse_mode="HTML")

@router.message(AdminStates.waiting_product_max_lzt)
async def prod_max_lzt(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: mx = float(message.text.strip().replace("$",""))
    except: return await message.answer("⚠️ Invalid")
    await state.update_data(new_max_lzt=mx)
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📦 Resale", callback_data="origin_resale"))
    b.row(InlineKeyboardButton(text="🤖 Autoreg", callback_data="origin_autoreg"))
    b.row(InlineKeyboardButton(text="👤 Personal", callback_data="origin_personal"))
    b.row(InlineKeyboardButton(text="🌐 Any Origin", callback_data="origin_any"))
    await message.answer(f"✅ Max: ${mx:.2f}\n\nSelect <b>account origin</b>:", reply_markup=b.as_markup(), parse_mode="HTML")



@router.callback_query(F.data.startswith("origin_"))
async def prod_origin(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    origin_map = {"origin_resale":"resale","origin_autoreg":"autoreg","origin_personal":"personal","origin_any":None}
    origin = origin_map.get(callback.data)
    data = await state.get_data()
    filters = {"nsb": 1}  # ALWAYS nsb=1 for OTP!
    if origin:
        filters["origin[]"] = origin
    success = add_product(data["new_code"], data["new_name"], data["new_flag"], data["new_price"], data["new_max_lzt"], filters)
    await state.clear()
    if success:
        await callback.message.edit_text(
            f"✅ <b>Added!</b>\n\n{data['new_flag']} {data['new_name']} ({data['new_code']})\n💵 ₹{data['new_price']:.0f} | Max ${data['new_max_lzt']:.2f}\n📦 Origin: {origin or 'Any'}\n🔑 OTP: ✅ Enabled",
            reply_markup=admin_back_keyboard(), parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ Failed (already exists?)", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

# ---- Remove Country ----
@router.callback_query(F.data == "prod_remove")
async def prod_remove_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    for p in get_all_products():
        b.row(InlineKeyboardButton(text=f"🗑️ {p['flag']} {p['name']}", callback_data=f"prod_del:{p['code']}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_products"))
    await callback.message.edit_text("🗑️ <b>Remove which?</b>", reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("prod_del:"))
async def prod_del(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    code = callback.data.split(":")[1]
    remove_product(code)
    await callback.message.edit_text(f"✅ Removed {code}", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

# ---- Change Price ----
@router.callback_query(F.data == "prod_price")
async def prod_price_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    for p in get_all_products():
        b.row(InlineKeyboardButton(text=f"💵 {p['flag']} {p['name']} — ₹{p['price']:.0f}", callback_data=f"prod_sp:{p['code']}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_products"))
    await callback.message.edit_text("💵 <b>Change price of?</b>", reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("prod_sp:"))
async def prod_sp(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    code = callback.data.split(":")[1]
    await state.update_data(price_code=code)
    await state.set_state(AdminStates.waiting_price_update)
    p = get_product(code)
    await callback.message.edit_text(f"💵 {p['flag']} {p['name']}\nCurrent: ₹{p['price']:.0f}\n\nSend new price:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_price_update)
async def prod_price_set(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: price = float(message.text.strip().replace("₹",""))
    except: return await message.answer("⚠️ Invalid")
    data = await state.get_data()
    update_product_price(data["price_code"], price)
    await state.clear()
    await message.answer(f"✅ {data['price_code']} → ₹{price:.0f}", reply_markup=admin_back_keyboard(), parse_mode="HTML")



def admin_panel_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📋 Pending Requests", callback_data="admin_pending"))
    b.row(InlineKeyboardButton(text="➕ Add Money", callback_data="admin_add_money"), InlineKeyboardButton(text="➖ Deduct Money", callback_data="admin_deduct_money"))
    b.row(InlineKeyboardButton(text="💰 Today Revenue", callback_data="admin_revenue"))
    b.row(InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"), InlineKeyboardButton(text="🔍 User Lookup", callback_data="admin_user_lookup"))
    b.row(InlineKeyboardButton(text="🛒 Product Manager", callback_data="admin_products"))
    b.row(InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"))
    return b.as_markup()

def admin_back_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_panel"))
    return b.as_markup()

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return await message.answer("⛔")
    await state.clear()
    await message.answer("🔐 <b>𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b>\n━━━━━━━━━━━━━━━━━━━━━", reply_markup=admin_panel_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "admin_panel")
async def panel_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.clear()
    await callback.message.edit_text("🔐 <b>𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b>\n━━━━━━━━━━━━━━━━━━━━━", reply_markup=admin_panel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_pending")
async def pending(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    db = await get_db()
    cur = await db.execute("SELECT d.id,d.amount,u.first_name FROM deposits d LEFT JOIN users u ON d.user_id=u.user_id WHERE d.status='PENDING' ORDER BY d.created_at DESC LIMIT 10")
    rows = await cur.fetchall()
    msg = "📋 <b>Pending</b>\n\n" + ("✅ None!" if not rows else "\n".join(f"#{r[0]} | {r[2]} | ₹{r[1]:.0f}" for r in rows))
    await callback.message.edit_text(msg, reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()



@router.callback_query(F.data == "admin_add_money")
async def add_money_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_user_id_add)
    await callback.message.edit_text("➕ <b>Add Money</b>\n\nSend User ID:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_user_id_add)
async def add_uid(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: uid = int(message.text.strip())
    except: return await message.answer("⚠️ Invalid")
    db = await get_db()
    row = await (await db.execute("SELECT first_name,wallet_balance FROM users WHERE user_id=?", (uid,))).fetchone()
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
    await message.answer(f"✅ +₹{amt:.0f} → ₹{new:.2f}", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    try: await message.bot.send_message(data["target_user_id"], f"💰 ₹{amt:.0f} added. Balance: ₹{new:.2f}", parse_mode="HTML")
    except: pass

@router.callback_query(F.data == "admin_deduct_money")
async def deduct_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_user_id_deduct)
    await callback.message.edit_text("➖ <b>Deduct</b>\n\nSend User ID:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_user_id_deduct)
async def deduct_uid(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: uid = int(message.text.strip())
    except: return await message.answer("⚠️ Invalid")
    db = await get_db()
    row = await (await db.execute("SELECT first_name,wallet_balance FROM users WHERE user_id=?", (uid,))).fetchone()
    if not row: return await message.answer("❌ Not found")
    await state.update_data(target_user_id=uid)
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
    await message.answer(f"✅ -₹{amt:.0f} → ₹{new:.2f}", reply_markup=admin_back_keyboard(), parse_mode="HTML")



@router.callback_query(F.data == "admin_revenue")
async def revenue(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    db = await get_db()
    today = date.today().isoformat()
    dep = await (await db.execute("SELECT COUNT(*),COALESCE(SUM(amount),0) FROM deposits WHERE status='APPROVED' AND DATE(created_at)=?", (today,))).fetchone()
    ords = await (await db.execute("SELECT COUNT(*),COALESCE(SUM(amount_paid),0) FROM orders WHERE DATE(created_at)=?", (today,))).fetchone()
    await callback.message.edit_text(f"💰 <b>Today ({today})</b>\n━━━━━━━━━━━━━━━━━━━━━\n✅ Deposits: {dep[0]} (₹{dep[1]:.0f})\n🛒 Sales: {ords[0]} (₹{ords[1]:.0f})", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    db = await get_db()
    users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
    ords = await (await db.execute("SELECT COUNT(*),COALESCE(SUM(amount_paid),0) FROM orders")).fetchone()
    await callback.message.edit_text(f"📊 <b>Stats</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 Users: {users}\n🛒 Orders: {ords[0]} (₹{ords[1]:.0f})", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_user_lookup")
async def lookup_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_user_lookup)
    await callback.message.edit_text("🔍 Send User ID:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_user_lookup)
async def lookup(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: uid = int(message.text.strip())
    except: return await message.answer("⚠️ Invalid")
    db = await get_db()
    u = await (await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))).fetchone()
    if not u: return await message.answer("❌ Not found")
    oc = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,))).fetchone())[0]
    await state.clear()
    await message.answer(f"🔍 <b>{u['first_name']}</b>\n🆔 <code>{uid}</code>\n💳 ₹{u['wallet_balance']:.2f}\n🛒 {oc} orders", reply_markup=admin_back_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.edit_text("📢 Send message to broadcast:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_broadcast)
async def broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    txt = message.text or ""
    if not txt: return
    await state.clear()
    db = await get_db()
    users = await (await db.execute("SELECT user_id FROM users")).fetchall()
    sent = sum(1 for r in users if await _try_send(message.bot, r[0], f"📢 {txt}"))
    await message.answer(f"📢 Sent to {sent}/{len(users)}", reply_markup=admin_back_keyboard(), parse_mode="HTML")

async def _try_send(bot, uid, txt):
    try:
        await bot.send_message(uid, txt, parse_mode="HTML")
        return True
    except: return False



# ==================== PRODUCT MANAGER ====================
@router.callback_query(F.data == "admin_products")
async def products_menu(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.clear()
    products = get_all_products()
    msg = "🛒 <b>Product Manager</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    for p in products:
        f_str = ", ".join(f"{k}={v}" for k,v in p.get("filters",{}).items())
        msg += f"{p['flag']} <b>{p['name']}</b> ({p['code']}) — ₹{p['price']:.0f}\n   🔧 {f_str}\n\n"
    if not products: msg += "📭 Empty\n"
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➕ Add Country", callback_data="prod_add"))
    if products:
        b.row(InlineKeyboardButton(text="🗑️ Remove", callback_data="prod_remove"))
        b.row(InlineKeyboardButton(text="💵 Change Price", callback_data="prod_price"))
        b.row(InlineKeyboardButton(text="🔧 Edit Filters", callback_data="prod_filters"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_panel"))
    await callback.message.edit_text(msg, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "prod_add")
async def prod_add_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_product_code)
    await callback.message.edit_text("➕ <b>Add Country</b>\n\nSend 2-letter code:\n📌 <code>US</code> <code>BD</code> <code>ID</code> <code>MM</code> <code>VN</code>", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_product_code)
async def pc_code(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    code = message.text.strip().upper()[:2]
    if len(code)!=2 or not code.isalpha(): return await message.answer("⚠️ 2 letters!")
    if get_product(code): return await message.answer(f"⚠️ {code} exists!")
    await state.update_data(new_code=code)
    await state.set_state(AdminStates.waiting_product_name)
    await message.answer(f"✅ {code}\n\nSend name (e.g. USA):")

@router.message(AdminStates.waiting_product_name)
async def pc_name(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.update_data(new_name=message.text.strip()[:30])
    await state.set_state(AdminStates.waiting_product_flag)
    await message.answer("✅ Send flag emoji (e.g. 🇺🇸):")

@router.message(AdminStates.waiting_product_flag)
async def pc_flag(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.update_data(new_flag=message.text.strip()[:4])
    await state.set_state(AdminStates.waiting_product_price)
    await message.answer("✅ Send <b>INR price</b> (user pays):\n📌 e.g. <code>70</code>", parse_mode="HTML")

@router.message(AdminStates.waiting_product_price)
async def pc_price(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: price = float(message.text.strip().replace("₹",""))
    except: return await message.answer("⚠️ Number please")
    await state.update_data(new_price=price)
    await state.set_state(AdminStates.waiting_product_max_lzt)
    await message.answer(f"✅ ₹{price:.0f}\n\nSend <b>max USD</b> (LZT cap):\n📌 e.g. <code>0.15</code>", parse_mode="HTML")

@router.message(AdminStates.waiting_product_max_lzt)
async def pc_max(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: mx = float(message.text.strip().replace("$",""))
    except: return await message.answer("⚠️ Number please")
    await state.update_data(new_max_lzt=mx)
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📦 Resale", callback_data="origin_resale"))
    b.row(InlineKeyboardButton(text="🤖 Autoreg", callback_data="origin_autoreg"))
    b.row(InlineKeyboardButton(text="👤 Personal", callback_data="origin_personal"))
    b.row(InlineKeyboardButton(text="🌐 Any", callback_data="origin_any"))
    await message.answer(f"✅ ${mx:.2f}\n\nSelect <b>origin</b>:", reply_markup=b.as_markup(), parse_mode="HTML")



@router.callback_query(F.data.startswith("origin_"))
async def pc_origin(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    o_map = {"origin_resale":"resale","origin_autoreg":"autoreg","origin_personal":"personal","origin_any":None}
    origin = o_map.get(callback.data)
    data = await state.get_data()
    filters = {"nsb": 1}  # ALWAYS nsb=1 so OTP works!
    if origin: filters["origin[]"] = origin
    success = add_product(data["new_code"], data["new_name"], data["new_flag"], data["new_price"], data["new_max_lzt"], filters)
    await state.clear()
    msg = f"✅ <b>Added!</b>\n\n{data['new_flag']} {data['new_name']} ({data['new_code']})\n₹{data['new_price']:.0f} | ${data['new_max_lzt']:.2f}\n📦 {origin or 'Any'} | 🔑 OTP: ✅" if success else "❌ Failed"
    await callback.message.edit_text(msg, reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "prod_remove")
async def prod_rm(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    for p in get_all_products():
        b.row(InlineKeyboardButton(text=f"🗑️ {p['flag']} {p['name']}", callback_data=f"prod_del:{p['code']}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_products"))
    await callback.message.edit_text("🗑️ Remove which?", reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("prod_del:"))
async def prod_del(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    remove_product(callback.data.split(":")[1])
    await callback.message.edit_text("✅ Removed!", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "prod_price")
async def prod_price_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    for p in get_all_products():
        b.row(InlineKeyboardButton(text=f"💵 {p['flag']} {p['name']} ₹{p['price']:.0f}", callback_data=f"prod_sp:{p['code']}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_products"))
    await callback.message.edit_text("💵 Change price of?", reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("prod_sp:"))
async def prod_sp(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    code = callback.data.split(":")[1]
    p = get_product(code)
    await state.update_data(price_code=code)
    await state.set_state(AdminStates.waiting_price_update)
    await callback.message.edit_text(f"{p['flag']} {p['name']} — ₹{p['price']:.0f}\n\nNew price:", reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_price_update)
async def price_set(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try: p = float(message.text.strip().replace("₹",""))
    except: return await message.answer("⚠️ Invalid")
    data = await state.get_data()
    update_product_price(data["price_code"], p)
    await state.clear()
    await message.answer(f"✅ {data['price_code']} → ₹{p:.0f}", reply_markup=admin_back_keyboard(), parse_mode="HTML")



# ==================== Deposit Approve/Reject ====================
@router.callback_query(F.data.startswith("admin_approve:"))
async def approve(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return await callback.answer("⛔", show_alert=True)
    parts = callback.data.split(":")
    if len(parts) != 4: return await callback.answer("❌", show_alert=True)
    deposit_id, user_id, amount = int(parts[1]), int(parts[2]), float(parts[3])
    db = await get_db()
    row = await (await db.execute("SELECT status FROM deposits WHERE id=?", (deposit_id,))).fetchone()
    if row and row[0] != "PENDING": return await callback.answer(f"Already {row[0]}", show_alert=True)
    await db.execute("UPDATE deposits SET status='APPROVED',admin_id=? WHERE id=? AND status='PENDING'", (callback.from_user.id, deposit_id))
    await db.commit()
    new_bal = await credit(user_id, amount)
    try: await callback.bot.send_message(user_id, format_deposit_approved(amount, new_bal), parse_mode="HTML")
    except: pass
    try: await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ APPROVED ₹{amount:.0f}", parse_mode="HTML", reply_markup=None)
    except: pass
    await callback.answer(f"✅ ₹{amount:.0f} approved", show_alert=True)

@router.callback_query(F.data.startswith("admin_reject:"))
async def reject(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return await callback.answer("⛔", show_alert=True)
    parts = callback.data.split(":")
    if len(parts) != 3: return await callback.answer("❌", show_alert=True)
    deposit_id, user_id = int(parts[1]), int(parts[2])
    db = await get_db()
    await db.execute("UPDATE deposits SET status='REJECTED',admin_id=? WHERE id=? AND status='PENDING'", (callback.from_user.id, deposit_id))
    await db.commit()
    try: await callback.bot.send_message(user_id, format_deposit_rejected(), parse_mode="HTML")
    except: pass
    try: await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ REJECTED", parse_mode="HTML", reply_markup=None)
    except: pass
    await callback.answer("❌ Rejected", show_alert=True)



# ==================== FILTER EDITOR ====================
# Available LZT Telegram filters (from website screenshot):
LZT_FILTERS = [
    {"key": "nsb", "val": 1, "label": "🟢 No Spam Block", "desc": "Only accounts WITHOUT spam block (login works)"},
    {"key": "sb", "val": 1, "label": "🔴 Has Spam Block", "desc": "Only accounts WITH spam block"},
    {"key": "origin[]", "val": "resale", "label": "📦 Resale", "desc": "Resold accounts (cheapest)"},
    {"key": "origin[]", "val": "autoreg", "label": "🤖 Autoreg", "desc": "Auto-registered (cleaner)"},
    {"key": "origin[]", "val": "personal", "label": "👤 Personal", "desc": "Real personal accounts"},
    {"key": "origin[]", "val": "stealer", "label": "🕵️ Stealer", "desc": "From stealers/phishing"},
    {"key": "telegram_password", "val": 1, "label": "🔐 Has 2FA Password", "desc": "Account has password"},
    {"key": "telegram_password", "val": 0, "label": "🔓 No Password", "desc": "No 2FA password"},
    {"key": "not_sold_before", "val": 1, "label": "🆕 Never Sold Before", "desc": "First-time sale only"},
    {"key": "telegram_premium", "val": 1, "label": "⭐ Has Premium", "desc": "Telegram Premium accounts only"},
]


@router.callback_query(F.data == "prod_filters")
async def filter_select_country(callback: CallbackQuery):
    """Select which country to edit filters for."""
    if callback.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    for p in get_all_products():
        b.row(InlineKeyboardButton(text=f"🔧 {p['flag']} {p['name']}", callback_data=f"filteredit:{p['code']}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_products"))
    await callback.message.edit_text("🔧 <b>Edit Filters</b>\n\nSelect country:", reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("filteredit:"))
async def filter_editor(callback: CallbackQuery):
    """Show filter toggle buttons for a country."""
    if callback.from_user.id not in ADMIN_IDS: return
    code = callback.data.split(":")[1]
    product = get_product(code)
    if not product:
        return await callback.answer("❌ Not found", show_alert=True)

    current_filters = product.get("filters", {})
    msg = f"🔧 <b>Filters: {product['flag']} {product['name']}</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "<b>Current:</b> "
    if current_filters:
        msg += ", ".join(f"{k}={v}" for k,v in current_filters.items())
    else:
        msg += "None (all accounts)"
    msg += "\n\n<b>Tap to toggle ON/OFF:</b>\n"

    b = InlineKeyboardBuilder()
    for f in LZT_FILTERS:
        # Check if this filter is currently active
        is_on = current_filters.get(f["key"]) == f["val"]
        icon = "✅" if is_on else "⬜"
        b.row(InlineKeyboardButton(
            text=f"{icon} {f['label']}",
            callback_data=f"ftoggle:{code}:{f['key']}:{f['val']}",
        ))

    b.row(InlineKeyboardButton(text="🗑️ Clear All Filters", callback_data=f"fclear:{code}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_products"))
    await callback.message.edit_text(msg, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("ftoggle:"))
async def filter_toggle(callback: CallbackQuery):
    """Toggle a filter on/off for a country."""
    if callback.from_user.id not in ADMIN_IDS: return
    parts = callback.data.split(":")
    code = parts[1]
    key = parts[2]
    val_str = parts[3]

    # Parse value (could be int or string)
    try:
        val = int(val_str)
    except ValueError:
        val = val_str

    product = get_product(code)
    if not product: return
    current_filters = product.get("filters", {}).copy()

    # Toggle: if key=val exists, remove it. Otherwise add it.
    # Special: origin[] can only have one value at a time
    if key == "origin[]":
        if current_filters.get(key) == val:
            del current_filters[key]
        else:
            current_filters[key] = val
    elif key in ("nsb", "sb"):
        # nsb and sb are mutually exclusive
        if current_filters.get(key) == val:
            del current_filters[key]
        else:
            current_filters.pop("nsb", None)
            current_filters.pop("sb", None)
            current_filters[key] = val
    elif key == "telegram_password":
        if current_filters.get(key) == val:
            del current_filters[key]
        else:
            current_filters[key] = val
    else:
        if current_filters.get(key) == val:
            del current_filters[key]
        else:
            current_filters[key] = val

    update_product_filters(code, current_filters)
    await callback.answer("✅ Updated!")

    # Re-render the filter editor
    product = get_product(code)
    current_filters = product.get("filters", {})
    msg = f"🔧 <b>Filters: {product['flag']} {product['name']}</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "<b>Current:</b> "
    msg += (", ".join(f"{k}={v}" for k,v in current_filters.items()) if current_filters else "None")
    msg += "\n\n<b>Tap to toggle ON/OFF:</b>\n"

    b = InlineKeyboardBuilder()
    for f in LZT_FILTERS:
        is_on = current_filters.get(f["key"]) == f["val"]
        icon = "✅" if is_on else "⬜"
        b.row(InlineKeyboardButton(text=f"{icon} {f['label']}", callback_data=f"ftoggle:{code}:{f['key']}:{f['val']}"))
    b.row(InlineKeyboardButton(text="🗑️ Clear All", callback_data=f"fclear:{code}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_products"))
    await callback.message.edit_text(msg, reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("fclear:"))
async def filter_clear(callback: CallbackQuery):
    """Clear all filters for a country."""
    if callback.from_user.id not in ADMIN_IDS: return
    code = callback.data.split(":")[1]
    update_product_filters(code, {})
    await callback.answer("🗑️ All filters cleared!")
    # Re-render
    product = get_product(code)
    msg = f"🔧 <b>Filters: {product['flag']} {product['name']}</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "<b>Current:</b> None (all accounts)\n\n<b>Tap to toggle ON/OFF:</b>\n"
    b = InlineKeyboardBuilder()
    for f in LZT_FILTERS:
        b.row(InlineKeyboardButton(text=f"⬜ {f['label']}", callback_data=f"ftoggle:{code}:{f['key']}:{f['val']}"))
    b.row(InlineKeyboardButton(text="🗑️ Clear All", callback_data=f"fclear:{code}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_products"))
    await callback.message.edit_text(msg, reply_markup=b.as_markup(), parse_mode="HTML")
