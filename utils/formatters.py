"""
Message formatting helpers with rich emojis.
"""

import json
from typing import Optional


def format_welcome(first_name: str, balance: float) -> str:
    """Format the welcome/start message."""
    return (
        f"👋 <b>Welcome, {first_name}!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛒 <b>Telegram Account Shop</b>\n"
        "Buy premium TG accounts instantly!\n\n"
        f"💳 <b>Wallet Balance:</b> ₹{balance:.2f}\n"
        "📦 <b>Status:</b> ✅ Active\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Select an option below:"
    )



def format_balance(balance: float) -> str:
    """Format balance check message."""
    return (
        "💳 <b>Your Wallet</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Balance:</b> ₹{balance:.2f}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Use <b>Deposit</b> to add funds."
    )


def format_deposit_info(upi_id: str, upi_name: str) -> str:
    """Format deposit instructions."""
    return (
        "💰 <b>Deposit Funds</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧾 <b>UPI ID:</b> <code>{upi_id}</code>\n"
        f"🧑‍💼 <b>Name:</b> {upi_name}\n\n"
        "📋 <b>Steps:</b>\n"
        f"1️⃣ Send money via UPI to <code>{upi_id}</code>\n"
        "2️⃣ Click <b>Make Deposit</b> and enter the exact amount\n"
        "3️⃣ Upload your UPI payment screenshot\n"
        "4️⃣ Admin verifies and approves the payment\n"
        "5️⃣ Balance is instantly credited to your wallet\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Click below to proceed:"
    )



def format_deposit_amount_prompt() -> str:
    """Prompt user for deposit amount."""
    return (
        "💸 <b>Enter Deposit Amount (₹)</b>\n\n"
        "📝 Type the exact amount you sent.\n"
        "📌 Example: <code>200</code>\n\n"
        "⚠️ Minimum deposit: ₹10"
    )


def format_deposit_screenshot_prompt(amount: float) -> str:
    """Prompt user for screenshot."""
    return (
        f"📸 <b>Amount: ₹{amount:.2f}</b>\n\n"
        "Please send the <b>payment screenshot</b> now.\n\n"
        "⚠️ Make sure the screenshot clearly shows:\n"
        "• Transaction amount\n"
        "• UPI reference/ID\n"
        "• Timestamp"
    )


def format_deposit_pending() -> str:
    """Deposit submitted confirmation."""
    return (
        "⏳ <b>Deposit Submitted!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Your deposit request has been sent to admin.\n"
        "You'll be notified once it's approved.\n\n"
        "💡 This usually takes a few minutes."
    )


def format_deposit_approved(amount: float, new_balance: float) -> str:
    """Deposit approved notification to user."""
    return (
        "🎉 <b>Deposit Approved!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 Amount: <b>₹{amount:.2f}</b>\n"
        f"💳 Current Balance: <b>₹{new_balance:.2f}</b>\n\n"
        "✅ Your wallet has been credited!"
    )


def format_deposit_rejected() -> str:
    """Deposit rejected notification to user."""
    return (
        "❌ <b>Deposit Rejected</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Your deposit was rejected.\n"
        "Please contact support or re-upload a clear screenshot.\n\n"
        "💡 Make sure the screenshot is clear and shows all details."
    )



def format_admin_deposit_notification(
    user_id: int, username: str, first_name: str, amount: float, deposit_id: int
) -> str:
    """Format deposit notification for admin group."""
    return (
        "🔔 <b>New Deposit Request</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>User:</b> {first_name} (@{username})\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💵 <b>Amount:</b> ₹{amount:.2f}\n"
        f"📋 <b>Deposit ID:</b> #{deposit_id}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Use buttons below to approve or reject."
    )


def format_shop_quality() -> str:
    """Format shop quality selection."""
    return (
        "📱 <b>TG Accounts</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ <b>Cheap Acc</b> — 🏷️ All origins, lowest price\n"
        "2️⃣ <b>Good Quality Acc</b> — ✨ Autoreg/Personal only\n\n"
        "⚠️ <b>NO REFUNDS IN ANY CASE.</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Select quality tier:"
    )


def format_shop_country(quality: str, price: float) -> str:
    """Format country selection."""
    quality_label = "⭐ Good Quality" if quality == "good" else "🎣 Cheap"
    return (
        f"🌍 <b>Select a Region</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Quality: {quality_label}\n"
        f"💵 Price: <b>₹{price:.2f}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Choose a country:"
    )



def format_country_search_prompt() -> str:
    """Prompt user to type country name."""
    return (
        "🔍 <b>Search Country</b>\n\n"
        "Please type the country name.\n"
        "📌 Example: <code>Russia</code> or <code>UK</code>"
    )


def format_insufficient_balance(required: float, current: float) -> str:
    """Insufficient balance message."""
    needed = required - current
    return (
        "⚠️ <b>Insufficient Balance</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 Required: ₹{required:.2f}\n"
        f"💳 Your Balance: ₹{current:.2f}\n"
        f"❌ Shortfall: ₹{needed:.2f}\n\n"
        "💡 Please deposit at least "
        f"₹{needed:.2f} using /deposit."
    )


def format_purchase_processing() -> str:
    """Purchase in progress message."""
    return "⏳ <b>Processing your purchase...</b>\n\nPlease wait."


def format_account_details(
    order_id: str, account_data: dict, price: float
) -> str:
    """Format purchased account details."""
    phone = account_data.get("phone", account_data.get("email", "N/A"))
    password = account_data.get("password", "N/A")
    twofa = account_data.get("2fa", account_data.get("totp", ""))

    msg = (
        "✅ <b>Purchase Successful!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>Order:</b> {order_id}\n"
        f"💵 <b>Paid:</b> ₹{price:.2f}\n\n"
        "📱 <b>Account Details:</b>\n"
        f"🔑 Phone/Email: <code>{phone}</code>\n"
        f"🔓 Password: <code>{password}</code>\n"
    )

    if twofa:
        msg += f"🔐 2FA Code: <code>{twofa}</code>\n"

    msg += (
        "\n━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Save these details! No refunds."
    )
    return msg


def format_purchase_failed_refund(amount: float, reason: str) -> str:
    """Purchase failed, refund issued."""
    return (
        "❌ <b>Purchase Failed</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Reason: {reason}\n"
        f"💵 Refund: <b>₹{amount:.2f}</b> returned to wallet.\n\n"
        "💡 Please try again or choose a different option."
    )



def format_order_list_header(count: int) -> str:
    """Header for order history."""
    return (
        "📋 <b>My Orders</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total Orders: {count}\n\n"
        "Click an order to view details:"
    )


def format_order_detail(order: dict) -> str:
    """Format single order detail view."""
    order_id = order.get("order_id", "N/A")
    amount = order.get("amount_paid", 0)
    quality = order.get("quality", "N/A")
    country = order.get("country", "N/A")
    date = order.get("created_at", "N/A")

    # Parse account data
    account_data = {}
    raw_data = order.get("account_data", "{}")
    if raw_data:
        try:
            account_data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        except (json.JSONDecodeError, TypeError):
            account_data = {}

    phone = account_data.get("phone", account_data.get("email", "N/A"))
    password = account_data.get("password", "N/A")
    twofa = account_data.get("2fa", account_data.get("totp", ""))

    msg = (
        f"📋 <b>Order Details</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Order: <b>{order_id}</b>\n"
        f"💵 Paid: ₹{amount:.2f}\n"
        f"📦 Quality: {quality}\n"
        f"🌍 Country: {country}\n"
        f"📅 Date: {date}\n\n"
        "📱 <b>Account Info:</b>\n"
        f"🔑 Phone/Email: <code>{phone}</code>\n"
        f"🔓 Password: <code>{password}</code>\n"
    )

    if twofa:
        msg += f"🔐 2FA: <code>{twofa}</code>\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━"
    return msg


def format_no_orders() -> str:
    """No orders message."""
    return (
        "📋 <b>My Orders</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📭 You haven't made any purchases yet.\n\n"
        "💡 Use <b>Buy TG Accounts</b> to get started!"
    )


def format_support() -> str:
    """Support message."""
    return (
        "🆘 <b>Support</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Need help? Contact us:\n\n"
        "📩 <b>Telegram:</b> @KaizenSeller\n"
        "⏰ <b>Response Time:</b> Within 1 hour\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Before contacting, please have your:\n"
        "• User ID (use /start to see)\n"
        "• Order ID (if relevant)\n"
        "• Screenshot of any issue"
    )
