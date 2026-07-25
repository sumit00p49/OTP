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
from services.product_manager import (
    get_all_products, get_product, add_product, remove_product,
    update_product_price, update_product_max_lzt,
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
    waiting_ban_user = State()
    # Add-country flow
    pc_code = State()
    pc_name = State()
    pc_flag = State()
    pc_price = State()
    pc_maxlzt = State()
    # Edit flows
    pc_edit_price = State()
    pc_edit_maxlzt = State()



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
    b.row(InlineKeyboardButton(text="🌍 Manage Countries", callback_data="pm_menu"))
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





# ==================== MANAGE COUNTRIES (no JSON editing!) ====================

def _pm_menu_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➕ Add Country", callback_data="pm_add"))
    b.row(InlineKeyboardButton(text="💵 Edit Price", callback_data="pm_editprice"),
          InlineKeyboardButton(text="💲 Edit Max LZT", callback_data="pm_editmax"))
    b.row(InlineKeyboardButton(text="🗑️ Remove Country", callback_data="pm_remove"))
    b.row(InlineKeyboardButton(text="🔍 Test Stock (debug)", callback_data="pm_teststock"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_panel"))
    return b.as_markup()


@router.callback_query(F.data == "pm_teststock")
async def pm_teststock(callback: CallbackQuery):
    """Show the EXACT filters + total the LZT API reports for each country,
    so you can compare the bot's query against the store view."""
    if callback.from_user.id not in ADMIN_IDS: return
    await callback.answer("🔍 Checking LZT...")
    from services.lzt_api import lzt_api
    from services.product_manager import get_effective_filters

    products = get_all_products()
    msg = "🔍 <b>Stock Debug (live from LZT)</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    for p in products:
        eff = get_effective_filters(p)
        info = await lzt_api.get_stock_debug(
            country=p["code"], pmax=p.get("max_lzt"), extra_filters=eff,
        )
        param_str = "&".join(f"{k}={v}" for k, v in info["params"].items())
        msg += f"{p.get('flag','')} <b>{p['name']}</b> (max ${p.get('max_lzt',0):.2f})\n"
        if info["error"]:
            msg += f"   ⚠️ Error: {info['error'][:60]}\n"
        else:
            msg += f"   📊 Total: <b>{info['total']}</b> | page: {info['items_on_page']}\n"
        msg += f"   <code>{param_str}</code>\n\n"
        import asyncio
        await asyncio.sleep(0.4)

    msg += "━━━━━━━━━━━━━━━━━━━━━\n💡 Compare 'Total' with the same filter on lzt.market."
    await callback.message.edit_text(msg, reply_markup=admin_back_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "pm_menu")
async def pm_menu(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.clear()
    products = get_all_products()
    msg = "🌍 <b>Manage Countries</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    if products:
        for p in products:
            msg += f"{p.get('flag','')} <b>{p['name']}</b> ({p['code']}) — ₹{p['price']:.0f} | max ${p.get('max_lzt',0):.2f}\n"
    else:
        msg += "📭 No countries yet.\n"
    msg += "\n➕ Add or 🗑️ remove below (no JSON editing needed):"
    await callback.message.edit_text(msg, reply_markup=_pm_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


# ---- Add Country flow ----
@router.callback_query(F.data == "pm_add")
async def pm_add(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.pc_code)
    await callback.message.edit_text(
        "➕ <b>Add Country</b>\n\nSend the 2-letter country code:\n"
        "📌 Examples: <code>US</code> <code>IN</code> <code>BD</code> <code>VN</code> <code>PK</code>",
        reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.pc_code)
async def pm_code(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    code = (message.text or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return await message.answer("⚠️ Send exactly 2 letters (e.g. US)")
    if get_product(code):
        return await message.answer(f"⚠️ {code} already exists! Remove it first or pick another.")
    await state.update_data(pc_code=code)
    await state.set_state(AdminStates.pc_name)
    await message.answer(f"✅ Code: <b>{code}</b>\n\nNow send the country NAME (e.g. Vietnam):", parse_mode="HTML")


@router.message(AdminStates.pc_name)
async def pm_name(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    name = (message.text or "").strip()[:30]
    if not name:
        return await message.answer("⚠️ Send a valid name.")
    await state.update_data(pc_name=name)
    await state.set_state(AdminStates.pc_flag)
    await message.answer(f"✅ Name: <b>{name}</b>\n\nNow send the FLAG emoji (e.g. 🇻🇳):", parse_mode="HTML")


@router.message(AdminStates.pc_flag)
async def pm_flag(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    flag = (message.text or "").strip()[:8]
    await state.update_data(pc_flag=flag)
    await state.set_state(AdminStates.pc_price)
    await message.answer("✅ Now send the PRICE in ₹ (what the user pays):\n📌 Example: <code>30</code>", parse_mode="HTML")


@router.message(AdminStates.pc_price)
async def pm_price(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        price = float((message.text or "").strip().replace("₹", ""))
    except (ValueError, TypeError):
        return await message.answer("⚠️ Send a valid number (e.g. 30)")
    await state.update_data(pc_price=price)
    await state.set_state(AdminStates.pc_maxlzt)
    await message.answer(
        f"✅ Price: ₹{price:.0f}\n\nNow send the MAX USD to pay on LZT:\n"
        "📌 Example: <code>0.18</code>\n"
        "<i>(higher = more stock; keep below your selling price)</i>",
        parse_mode="HTML")


@router.message(AdminStates.pc_maxlzt)
async def pm_maxlzt(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        max_lzt = float((message.text or "").strip().replace("$", ""))
    except (ValueError, TypeError):
        return await message.answer("⚠️ Send a valid number (e.g. 0.18)")
    data = await state.get_data()
    ok = add_product(
        data["pc_code"], data["pc_name"], data.get("pc_flag", "🌍"),
        data["pc_price"], max_lzt, {},
    )
    await state.clear()
    if ok:
        await message.answer(
            f"✅ <b>Country Added!</b>\n\n"
            f"{data.get('pc_flag','🌍')} <b>{data['pc_name']}</b> ({data['pc_code']})\n"
            f"💵 ₹{data['pc_price']:.0f} | max ${max_lzt:.2f}\n"
            f"🔧 Filters: nsb=1, spam=no, email=yes (auto)\n\n"
            "It shows in the shop right away. No restart needed!",
            reply_markup=admin_back_keyboard(), parse_mode="HTML")
    else:
        await message.answer("❌ Failed (already exists?)", reply_markup=admin_back_keyboard(), parse_mode="HTML")


# ---- Remove Country flow ----
@router.callback_query(F.data == "pm_remove")
async def pm_remove_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    for p in get_all_products():
        b.row(InlineKeyboardButton(
            text=f"🗑️ {p.get('flag','')} {p['name']} ({p['code']})",
            callback_data=f"pm_del:{p['code']}",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="pm_menu"))
    await callback.message.edit_text("🗑️ <b>Tap a country to remove it:</b>", reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pm_del:"))
async def pm_del(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    code = callback.data.split(":")[1]
    removed = remove_product(code)
    await callback.answer("🗑️ Removed!" if removed else "Not found", show_alert=True)
    # Re-render the country list
    products = get_all_products()
    msg = "🌍 <b>Manage Countries</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    if products:
        for p in products:
            msg += f"{p.get('flag','')} <b>{p['name']}</b> ({p['code']}) — ₹{p['price']:.0f} | max ${p.get('max_lzt',0):.2f}\n"
    else:
        msg += "📭 No countries yet.\n"
    msg += "\n➕ Add or 🗑️ remove below (no JSON editing needed):"
    await callback.message.edit_text(msg, reply_markup=_pm_menu_keyboard(), parse_mode="HTML")



# ---- Edit Price flow ----
@router.callback_query(F.data == "pm_editprice")
async def pm_editprice_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    for p in get_all_products():
        b.row(InlineKeyboardButton(
            text=f"{p.get('flag','')} {p['name']} — ₹{p['price']:.0f}",
            callback_data=f"pm_sp:{p['code']}",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="pm_menu"))
    await callback.message.edit_text("💵 <b>Tap a country to change its ₹ price:</b>", reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pm_sp:"))
async def pm_sp(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    code = callback.data.split(":")[1]
    p = get_product(code)
    if not p:
        return await callback.answer("Not found", show_alert=True)
    await state.update_data(edit_code=code)
    await state.set_state(AdminStates.pc_edit_price)
    await callback.message.edit_text(
        f"{p.get('flag','')} <b>{p['name']}</b>\nCurrent price: ₹{p['price']:.0f}\n\n"
        "Send the NEW price in ₹:\n📌 Example: <code>35</code>",
        reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.pc_edit_price)
async def pm_set_price(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        price = float((message.text or "").strip().replace("₹", ""))
    except (ValueError, TypeError):
        return await message.answer("⚠️ Send a valid number (e.g. 35)")
    data = await state.get_data()
    code = data.get("edit_code", "")
    update_product_price(code, price)
    await state.clear()
    await message.answer(
        f"✅ {code} price updated → ₹{price:.0f}\n(Shows in shop right away.)",
        reply_markup=admin_back_keyboard(), parse_mode="HTML")


# ---- Edit Max LZT flow ----
@router.callback_query(F.data == "pm_editmax")
async def pm_editmax_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    for p in get_all_products():
        b.row(InlineKeyboardButton(
            text=f"{p.get('flag','')} {p['name']} — ${p.get('max_lzt',0):.2f}",
            callback_data=f"pm_sm:{p['code']}",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="pm_menu"))
    await callback.message.edit_text(
        "💲 <b>Tap a country to change its Max LZT (USD)</b>\n"
        "<i>Higher = more stock. Keep below your selling price.</i>",
        reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pm_sm:"))
async def pm_sm(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    code = callback.data.split(":")[1]
    p = get_product(code)
    if not p:
        return await callback.answer("Not found", show_alert=True)
    await state.update_data(edit_code=code)
    await state.set_state(AdminStates.pc_edit_maxlzt)
    await callback.message.edit_text(
        f"{p.get('flag','')} <b>{p['name']}</b>\nCurrent max LZT: ${p.get('max_lzt',0):.2f}\n\n"
        "Send the NEW max USD:\n📌 Example: <code>0.20</code>",
        reply_markup=admin_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.pc_edit_maxlzt)
async def pm_set_maxlzt(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        mx = float((message.text or "").strip().replace("$", ""))
    except (ValueError, TypeError):
        return await message.answer("⚠️ Send a valid number (e.g. 0.20)")
    data = await state.get_data()
    code = data.get("edit_code", "")
    update_product_max_lzt(code, mx)
    await state.clear()
    await message.answer(
        f"✅ {code} max LZT updated → ${mx:.2f}\n(More stock if you raised it.)",
        reply_markup=admin_back_keyboard(), parse_mode="HTML")
