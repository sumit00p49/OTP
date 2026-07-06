"""
All inline keyboard builders for the bot.
Organized by feature: main menu, deposit, shop, orders, etc.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ==================== Main Menu ====================

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu inline keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📱 Buy TG Accounts", callback_data="shop_main")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Deposit Funds", callback_data="deposit_start"),
        InlineKeyboardButton(text="💳 My Balance", callback_data="check_balance"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 My Orders", callback_data="my_orders")
    )
    builder.row(
        InlineKeyboardButton(text="🆘 Support", callback_data="support")
    )
    return builder.as_markup()


# ==================== Deposit ====================

def deposit_menu_keyboard() -> InlineKeyboardMarkup:
    """Deposit info menu with Make Deposit and Back buttons."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💸 Make Deposit", callback_data="deposit_amount")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")
    )
    return builder.as_markup()


def deposit_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button during deposit flow."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data="deposit_cancel")
    )
    return builder.as_markup()


def admin_deposit_keyboard(deposit_id: int, user_id: int, amount: float) -> InlineKeyboardMarkup:
    """Admin approve/reject buttons for deposits."""
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


# ==================== Shop ====================

def shop_quality_keyboard() -> InlineKeyboardMarkup:
    """Quality selection for TG accounts."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎣 Cheap Acc", callback_data="quality_cheap"),
        InlineKeyboardButton(text="⭐ Good Quality", callback_data="quality_good"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")
    )
    return builder.as_markup()


def shop_country_keyboard() -> InlineKeyboardMarkup:
    """Country selection grid."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇮🇳 India", callback_data="country_IN"),
        InlineKeyboardButton(text="🇺🇸 USA", callback_data="country_US"),
    )
    builder.row(
        InlineKeyboardButton(text="🇮🇩 Indonesia", callback_data="country_ID"),
        InlineKeyboardButton(text="🇲🇲 Myanmar", callback_data="country_MM"),
    )
    builder.row(
        InlineKeyboardButton(text="🇧🇩 Bangladesh", callback_data="country_BD"),
        InlineKeyboardButton(text="🇻🇳 Vietnam", callback_data="country_VN"),
    )
    builder.row(
        InlineKeyboardButton(text="🌐 Random", callback_data="country_RANDOM")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Search All Countries", callback_data="country_search")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="shop_main")
    )
    return builder.as_markup()


def confirm_purchase_keyboard() -> InlineKeyboardMarkup:
    """Confirm purchase button. The pending purchase is stored in FSM state."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Confirm & Buy", callback_data="confirm_buy_pending")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="shop_main")
    )
    return builder.as_markup()


def account_received_keyboard(order_id: str, item_id: str = "") -> InlineKeyboardMarkup:
    """Buttons shown after an account is delivered."""
    builder = InlineKeyboardBuilder()
    if item_id:
        builder.row(
            InlineKeyboardButton(text="🔄 Get Live OTP", callback_data=f"get_otp:{item_id}")
        )
    builder.row(
        InlineKeyboardButton(text="📋 Save to Orders", callback_data=f"save_order:{order_id}"),
        InlineKeyboardButton(text="🗑️ Account Received", callback_data="account_ack"),
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
                text=f"🟢 {order_id} | ₹{amount:.2f}",
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
    """Single order detail view with a live OTP button."""
    builder = InlineKeyboardBuilder()
    if item_id:
        builder.row(
            InlineKeyboardButton(text="🔄 Get Live OTP", callback_data=f"get_otp:{item_id}")
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
    """Support view."""
    builder = InlineKeyboardBuilder()
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
