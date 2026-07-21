"""
All inline keyboard builders for the bot.
Simplified: India-only TG Premium accounts at fixed ₹60.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.product_manager import get_all_products


# ==================== Main Menu ====================

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu inline keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📱 𝐁𝐮𝐲 𝐓𝐞𝐥𝐞𝐠𝐫𝐚𝐦 𝐀𝐜𝐜𝐨𝐮𝐧𝐭",
            callback_data="buy_account",
        )
    )
    builder.row(
        InlineKeyboardButton(text="💰 𝖣𝖾𝗉𝗈𝗌𝗂𝗍", callback_data="deposit_start"),
        InlineKeyboardButton(text="💳 𝖶𝖺𝗅𝗅𝖾𝗍", callback_data="check_balance"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 𝖮𝗋𝖽𝖾𝗋 𝖧𝗂𝗌𝗍𝗈𝗋𝗒", callback_data="my_orders"),
        InlineKeyboardButton(text="🎟️ 𝖱𝖾𝖿𝖿𝖾𝗋𝖺𝗅", callback_data="my_referral"),
    )
    builder.row(
        InlineKeyboardButton(text="🆘 𝖲𝗎𝗉𝗉𝗈𝗋𝗍", callback_data="support")
    )
    return builder.as_markup()


# ==================== Buy / Country Selection ====================

def buy_country_keyboard() -> InlineKeyboardMarkup:
    """Dynamically generate country buttons with full name + price."""
    builder = InlineKeyboardBuilder()
    for product in get_all_products():
        flag = product.get("flag", "🌍")
        name = product.get("name", product["code"])
        price = product.get("price", 0)
        code = product["code"]
        builder.row(
            InlineKeyboardButton(
                text=f"{flag} {name}  —  ₹{price:.0f}",
                callback_data=f"select_country:{code}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ 𝗕𝗮𝗰𝗸", callback_data="back_main")
    )
    return builder.as_markup()


# ==================== Buy / Quantity ====================

def quantity_select_keyboard() -> InlineKeyboardMarkup:
    """Quantity selection grid."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1️⃣", callback_data="qty:1"),
        InlineKeyboardButton(text="2️⃣", callback_data="qty:2"),
        InlineKeyboardButton(text="3️⃣", callback_data="qty:3"),
    )
    builder.row(
        InlineKeyboardButton(text="5️⃣", callback_data="qty:5"),
        InlineKeyboardButton(text="🔟", callback_data="qty:10"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Custom Quantity", callback_data="qty:custom")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")
    )
    return builder.as_markup()


def buy_confirm_keyboard(qty: int, total: float, country_code: str = "IN") -> InlineKeyboardMarkup:
    """Confirm purchase with quantity, total, and country."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"✅ Pay ₹{total:.0f} for {qty} acc",
            callback_data=f"confirm_buy:{qty}:{country_code}",
        )
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="buy_account")
    )
    return builder.as_markup()


def account_delivered_keyboard(order_id: str, item_id: str = "") -> InlineKeyboardMarkup:
    """Buttons shown after account is delivered."""
    builder = InlineKeyboardBuilder()
    if item_id:
        builder.row(
            InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}")
        )
        builder.row(
            InlineKeyboardButton(text="📱 Manage Sessions", callback_data=f"devices:{item_id}"),
        )
    builder.row(
        InlineKeyboardButton(text="👍 Good", callback_data=f"rate:{order_id}:good"),
        InlineKeyboardButton(text="👎 Bad", callback_data=f"rate:{order_id}:bad"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Menu", callback_data="back_main"),
    )
    return builder.as_markup()


# ==================== Deposit ====================

def deposit_menu_keyboard() -> InlineKeyboardMarkup:
    """Deposit info menu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💸 𝗠𝗮𝗸𝗲 𝗗𝗲𝗽𝗼𝘀𝗶𝘁", callback_data="deposit_amount")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ 𝗕𝗮𝗰𝗸", callback_data="back_main")
    )
    return builder.as_markup()


def deposit_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button during deposit flow."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ 𝗖𝗮𝗻𝗰𝗲𝗹", callback_data="deposit_cancel")
    )
    return builder.as_markup()


def deposit_check_keyboard() -> InlineKeyboardMarkup:
    """Check Now button - shown after QR with amount. User sends screenshot after paying."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ 𝗖𝗵𝗲𝗰𝗸 𝗡𝗼𝘄", callback_data="deposit_check_now")
    )
    builder.row(
        InlineKeyboardButton(text="❌ 𝗖𝗮𝗻𝗰𝗲𝗹", callback_data="deposit_cancel")
    )
    return builder.as_markup()


def admin_deposit_keyboard(deposit_id: int, user_id: int, amount: float) -> InlineKeyboardMarkup:
    """Admin approve/reject buttons."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"✅ Approve (₹{amount:.2f})",
            callback_data=f"admin_approve:{deposit_id}:{user_id}:{amount}",
        ),
        InlineKeyboardButton(
            text="❌ Reject",
            callback_data=f"admin_reject:{deposit_id}:{user_id}",
        ),
    )
    return builder.as_markup()


# ==================== Orders ====================

def orders_list_keyboard(orders: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Order history list with pagination."""
    builder = InlineKeyboardBuilder()

    start = page * per_page
    end = start + per_page
    page_orders = orders[start:end]

    for order in page_orders:
        order_id = order.get("order_id", "N/A")
        amount = order.get("amount_paid", 0)
        builder.row(
            InlineKeyboardButton(
                text=f"🟢 {order_id} | ₹{amount:.0f}",
                callback_data=f"order_detail:{order_id}",
            )
        )

    # Pagination
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Prev", callback_data=f"orders_page:{page - 1}")
        )
    if end < len(orders):
        nav_buttons.append(
            InlineKeyboardButton(text="Next ➡️", callback_data=f"orders_page:{page + 1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")
    )
    return builder.as_markup()


def order_detail_keyboard(order_id: str, item_id: str = "") -> InlineKeyboardMarkup:
    """Single order detail view with Get OTP + Manage Sessions buttons."""
    builder = InlineKeyboardBuilder()
    if item_id:
        builder.row(
            InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}")
        )
        builder.row(
            InlineKeyboardButton(text="📱 Manage Sessions", callback_data=f"devices:{item_id}"),
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="my_orders")
    )
    return builder.as_markup()


# ==================== Balance ====================

def balance_keyboard() -> InlineKeyboardMarkup:
    """Balance view with deposit option."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Deposit", callback_data="deposit_start")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")
    )
    return builder.as_markup()


# ==================== Support ====================

def support_keyboard() -> InlineKeyboardMarkup:
    """Support - opens DM to admin directly."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💬 Chat with Support", url="https://t.me/OverrMaxx")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")
    )
    return builder.as_markup()


# ==================== Generic ====================

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Simple back to main menu button."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")
    )
    return builder.as_markup()
