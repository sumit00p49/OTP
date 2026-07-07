"""
Message formatting helpers with rich emojis.
Simplified for India-only TG Premium accounts at fixed ₹60.
Supports Telegram Premium custom emojis via entities.
"""

import json
from aiogram.types import MessageEntity


# ==================== Custom Emoji IDs ====================
# You can find custom emoji IDs by sending them to @RawDataBot
# These are Telegram Premium animated emojis
EMOJI_STAR = "5368324170671202286"       # ✨ animated star
EMOJI_LIGHTNING = "5368324170671202286"   # ⚡ lightning
EMOJI_LOCK = "5367811040498488737"        # 🔐 lock
EMOJI_CHECK = "5368324170671202286"      # ✅ check


def build_welcome_entities(first_name: str, balance: float) -> tuple[str, list[MessageEntity]]:
    """
    Build the welcome message with Telegram Premium custom emojis.
    Returns (text, entities) tuple for use without parse_mode.
    """
    # Build the text with placeholder emojis (single char each)
    lines = [
        f"👋 Welcome, {first_name}!\n",
        "\n",
        "✨ 𝙋𝙧𝙚𝙢𝙞𝙪𝙢 𝙏𝙚𝙡𝙚𝙜𝙧𝙖𝙢 𝙄𝘿𝙨\n",
        "✨ 𝙑𝙞𝙧𝙩𝙪𝙖𝙡 𝙉𝙪𝙢𝙗𝙚𝙧 𝙑𝙚𝙧𝙞𝙛𝙞𝙚𝙙\n",
        "✨ 𝘽𝙪𝙡𝙠 𝙊𝙧𝙙𝙚𝙧 𝙊𝙛𝙛𝙚𝙧𝙨\n",
        "✨ 𝙄𝙣𝙨𝙩𝙖𝙣𝙩 𝘿𝙚𝙡𝙞𝙫𝙚𝙧𝙮\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "    ⚡ 𝟮𝟰/𝟳  •  🔐 𝟭𝟬𝟬% 𝗦𝗮𝗳𝗲\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "\n",
        f"💳 Balance: ₹{balance:.2f}\n",
        f"📦 Status: ⭐ Active\n",
    ]

    text = "".join(lines)

    # Build entities for custom emojis
    # Find positions of ✨ characters and replace with custom emoji entities
    entities = []

    # Find all ✨ positions
    offset = 0
    for i, char in enumerate(text):
        if char == "✨":
            entities.append(MessageEntity(
                type="custom_emoji",
                offset=i,
                length=1,
                custom_emoji_id=EMOJI_STAR,
            ))
        elif char == "⚡":
            entities.append(MessageEntity(
                type="custom_emoji",
                offset=i,
                length=1,
                custom_emoji_id=EMOJI_LIGHTNING,
            ))
        elif char == "🔐":
            entities.append(MessageEntity(
                type="custom_emoji",
                offset=i,
                length=1,
                custom_emoji_id=EMOJI_LOCK,
            ))
        elif char == "⭐":
            entities.append(MessageEntity(
                type="custom_emoji",
                offset=i,
                length=1,
                custom_emoji_id=EMOJI_CHECK,
            ))

    # Add bold for "Welcome, name"
    welcome_text = f"Welcome, {first_name}!"
    welcome_offset = text.find(welcome_text)
    if welcome_offset >= 0:
        entities.append(MessageEntity(
            type="bold",
            offset=welcome_offset,
            length=len(welcome_text),
        ))

    # Bold for Balance amount
    bal_text = f"₹{balance:.2f}"
    bal_offset = text.find(bal_text)
    if bal_offset >= 0:
        entities.append(MessageEntity(
            type="bold",
            offset=bal_offset,
            length=len(bal_text),
        ))

    return text, entities


def format_welcome_text(first_name: str, balance: float) -> str:
    """Fallback plain-text welcome (used where entities aren't supported)."""
    return (
        f"👋 Welcome, {first_name}!\n\n"
        "✨ 𝙋𝙧𝙚𝙢𝙞𝙪𝙢 𝙏𝙚𝙡𝙚𝙜𝙧𝙖𝙢 𝙄𝘿𝙨\n"
        "✨ 𝙑𝙞𝙧𝙩𝙪𝙖𝙡 𝙉𝙪𝙢𝙗𝙚𝙧 𝙑𝙚𝙧𝙞𝙛𝙞𝙚𝙙\n"
        "✨ 𝘽𝙪𝙡𝙠 𝙊𝙧𝙙𝙚𝙧 𝙊𝙛𝙛𝙚𝙧𝙨\n"
        "✨ 𝙄𝙣𝙨𝙩𝙖𝙣𝙩 𝘿𝙚𝙡𝙞𝙫𝙚𝙧𝙮\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "    ⚡ 𝟮𝟰/𝟳  •  🔐 𝟭𝟬𝟬% 𝗦𝗮𝗳𝗲\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 Balance: ₹{balance:.2f}\n"
        "📦 Status: ⭐ Active"
    )


def format_quantity_select(price_per: float) -> str:
    """Quantity selection screen."""
    return (
        "📱✨ <b>Buy India TG Accounts</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🇮🇳 <b>Country:</b> India (+91)\n"
        "🔐 <b>Includes:</b> Password + Login Code\n"
        f"💵 <b>Price:</b> ₹{price_per:.0f} per account\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📦 <b>How many accounts do you want?</b>"
    )


def format_buy_confirm(qty: int, price_per: float, total: float, balance: float) -> str:
    """Purchase confirmation with quantity & total."""
    return (
        "🛒 <b>Confirm Purchase</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>Quantity:</b> {qty} account{'s' if qty > 1 else ''}\n"
        f"💵 <b>Price:</b> {qty} × ₹{price_per:.0f} = <b>₹{total:.0f}</b>\n"
        f"💳 <b>Balance:</b> ₹{balance:.2f}\n\n"
        "⚠️ <b>NO REFUNDS AFTER PURCHASE</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Click below to pay:"
    )


def format_purchase_processing_multi(qty: int) -> str:
    """Multi-account purchase in progress."""
    return (
        f"⏳ <b>Buying {qty} account{'s' if qty > 1 else ''}...</b>\n\n"
        "🔄 Fetching from store. Please wait.\n"
        "This may take 10-30 seconds."
    )


def format_multi_account_details(delivered: list, price_per: float, header: str = "") -> str:
    """Summary for multiple accounts delivered."""
    total = price_per * len(delivered)
    msg = header or ""
    msg += (
        f"✅ <b>{len(delivered)} Account{'s' if len(delivered) > 1 else ''} Delivered!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 <b>Total Paid:</b> ₹{total:.0f}\n\n"
        "📱 Accounts sent as separate messages below ⬇️\n"
        "Each has a <b>🔄 Get Live OTP</b> button.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 All orders saved in 📋 My Orders."
    )
    return msg


def format_partial_delivery(delivered: int, failed: int, refund: float) -> str:
    """Header when some accounts failed."""
    return (
        f"⚠️ <b>Partial Delivery</b>\n"
        f"✅ Delivered: {delivered} | ❌ Failed: {failed}\n"
        f"💵 Refund for failed: <b>₹{refund:.0f}</b> (auto-credited)\n\n"
    )


def format_buy_preview(price: float, balance: float) -> str:
    """Purchase confirmation screen."""
    return (
        "📱✨ <b>Buy India TG Account</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🇮🇳 <b>Country:</b> India (+91)\n"
        "📦 <b>Type:</b> Telegram Account\n"
        "🔐 <b>Includes:</b> Password + Login Code\n"
        f"💵 <b>Price:</b> ₹{price:.0f}\n\n"
        f"💳 Your Balance: ₹{balance:.2f}\n\n"
        "⚠️ <b>NO REFUNDS AFTER PURCHASE</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Click below to confirm:"
    )


def format_purchase_processing() -> str:
    """Purchase in progress."""
    return (
        "⏳ <b>Processing your purchase...</b>\n\n"
        "🔄 Fetching account from store...\n"
        "Please wait 5-10 seconds."
    )


def format_account_details(order_id: str, account_data: dict, price: float) -> str:
    """Format delivered account details."""
    phone = account_data.get("phone", "N/A")
    password = account_data.get("password", "")
    twofa = account_data.get("2fa", "")
    login_code = account_data.get("login_code", "")
    item_id = account_data.get("item_id", "")
    has_tdata = account_data.get("has_tdata", False)

    msg = (
        "✅ <b>Purchase Successful!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>Order:</b> {order_id}\n"
        f"💵 <b>Paid:</b> ₹{price:.0f}\n"
        "🇮🇳 <b>Country:</b> India\n\n"
        "📱 <b>Account Details:</b>\n"
        f"📞 Phone: <code>{phone}</code>\n"
    )
    if password and password != "N/A":
        msg += f"🔓 Password: <code>{password}</code>\n"
    if twofa:
        msg += f"🔐 2FA: <code>{twofa}</code>\n"
    if login_code:
        msg += f"📲 Login Code: <code>{login_code}</code>\n"
    if has_tdata and item_id:
        msg += f"💾 TData: <code>https://lzt.market/{item_id}/</code>\n"

    msg += (
        "\n━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Use <b>🔄 Get Live OTP</b> button anytime for\n"
        "a fresh login code.\n"
        "⚠️ Save these details! No refunds."
    )
    return msg


def format_purchase_failed_refund(amount: float, reason: str) -> str:
    """Purchase failed, refund issued."""
    return (
        "❌ <b>Purchase Failed</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Reason: {reason}\n\n"
        f"💵 Refund: <b>₹{amount:.0f}</b> returned to your wallet.\n\n"
        "💡 Try again or contact support."
    )


def format_out_of_stock() -> str:
    """Out of stock message."""
    return (
        "❌ <b>Out of Stock</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "No India accounts available right now.\n\n"
        "💡 Check back in 5-10 minutes.\n"
        "✅ No money was deducted from your wallet."
    )


def format_insufficient_balance(required: float, current: float) -> str:
    """Insufficient balance message."""
    needed = required - current
    return (
        "⚠️ <b>Insufficient Balance</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 Required: ₹{required:.0f}\n"
        f"💳 Your Balance: ₹{current:.2f}\n"
        f"❌ Need: ₹{needed:.2f} more\n\n"
        "💡 Use <b>💰 Deposit Funds</b> to add balance."
    )


# ==================== Balance ====================

def format_balance(balance: float) -> str:
    """Format balance check."""
    return (
        "💳 <b>Your Wallet</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Balance:</b> ₹{balance:.2f}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Use <b>Deposit</b> to add funds."
    )


# ==================== Deposit ====================

def format_deposit_info(upi_id: str, upi_name: str) -> str:
    """Format deposit instructions."""
    return (
        "💰 <b>Deposit Funds</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧾 <b>UPI ID:</b> <code>{upi_id}</code>\n"
        f"🧑‍💼 <b>Name:</b> {upi_name}\n\n"
        "📋 <b>Steps:</b>\n"
        f"1️⃣ Send money via UPI to <code>{upi_id}</code>\n"
        "2️⃣ Click <b>Make Deposit</b> and enter amount\n"
        "3️⃣ Upload your payment screenshot\n"
        "4️⃣ Admin verifies and approves\n"
        "5️⃣ Balance credited instantly!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Click below to proceed:"
    )


def format_deposit_amount_prompt() -> str:
    """Prompt for deposit amount."""
    return (
        "💸 <b>Enter Deposit Amount (₹)</b>\n\n"
        "📝 Type the exact amount you sent.\n"
        "📌 Example: <code>100</code>\n\n"
        "⚠️ Minimum deposit: ₹10"
    )


def format_deposit_screenshot_prompt(amount: float) -> str:
    """Prompt for screenshot."""
    return (
        f"📸 <b>Amount: ₹{amount:.2f}</b>\n\n"
        "Send the <b>payment screenshot</b> now.\n\n"
        "⚠️ Make sure it clearly shows:\n"
        "• Transaction amount\n"
        "• UPI reference/ID\n"
        "• Timestamp"
    )


def format_deposit_pending() -> str:
    """Deposit submitted confirmation."""
    return (
        "⏳ <b>Deposit Submitted!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Sent to admin for verification.\n"
        "You'll be notified once approved.\n\n"
        "💡 Usually takes 2-5 minutes."
    )


def format_deposit_approved(amount: float, new_balance: float) -> str:
    """Deposit approved notification."""
    return (
        "🎉 <b>Deposit Approved!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 Amount: <b>₹{amount:.2f}</b>\n"
        f"💳 New Balance: <b>₹{new_balance:.2f}</b>\n\n"
        "✅ Your wallet has been credited!"
    )


def format_deposit_rejected() -> str:
    """Deposit rejected notification."""
    return (
        "❌ <b>Deposit Rejected</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Your deposit was rejected.\n"
        "Please contact support or upload a clearer screenshot."
    )


def format_admin_deposit_notification(
    user_id: int, username: str, first_name: str, amount: float, deposit_id: int
) -> str:
    """Format deposit notification for admin."""
    return (
        "🔔 <b>New Deposit Request</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>User:</b> {first_name} (@{username})\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💵 <b>Amount:</b> ₹{amount:.2f}\n"
        f"📋 <b>Deposit ID:</b> #{deposit_id}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Approve or reject below:"
    )


# ==================== Orders ====================

def format_order_list_header(count: int) -> str:
    """Header for order history."""
    return (
        "📋 <b>My Orders</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total Orders: {count}\n\n"
        "Click an order to view details:"
    )


def format_order_detail(order: dict) -> str:
    """Format single order detail."""
    order_id = order.get("order_id", "N/A")
    amount = order.get("amount_paid", 0)
    date = order.get("created_at", "N/A")

    account_data = {}
    raw = order.get("account_data", "{}")
    if raw:
        try:
            account_data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            account_data = {}

    phone = account_data.get("phone", "N/A")
    password = account_data.get("password", "")
    twofa = account_data.get("2fa", "")
    login_code = account_data.get("login_code", "")
    item_id = account_data.get("item_id", "")
    has_tdata = account_data.get("has_tdata", False)

    msg = (
        f"📋 <b>Order Details</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Order: <b>{order_id}</b>\n"
        f"💵 Paid: ₹{amount:.0f}\n"
        f"🇮🇳 Country: India\n"
        f"📅 Date: {date}\n\n"
        "📱 <b>Account Info:</b>\n"
        f"📞 Phone: <code>{phone}</code>\n"
    )
    if password and password != "N/A":
        msg += f"🔓 Password: <code>{password}</code>\n"
    if twofa:
        msg += f"🔐 2FA: <code>{twofa}</code>\n"
    if login_code:
        msg += f"📲 Login Code: <code>{login_code}</code>\n"
    if has_tdata and item_id:
        msg += f"💾 TData: <code>https://lzt.market/{item_id}/</code>\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━"
    return msg


def format_no_orders() -> str:
    """No orders message."""
    return (
        "📋 <b>My Orders</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📭 No purchases yet.\n\n"
        "💡 Use <b>📱✨ Buy TG Premium Acc</b> to get started!"
    )


# ==================== Live OTP ====================

def format_live_otp(code: str) -> str:
    """Fresh live OTP received."""
    return (
        "📲 <b>Live OTP Received!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔐 Code: <code>{code}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Tap the code to copy.\n"
        "Press <b>🔄 Get Live OTP</b> for a new one."
    )


def format_otp_not_ready() -> str:
    """No OTP available yet."""
    return (
        "⏳ <b>No OTP Yet</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Login code hasn't arrived yet.\n\n"
        "💡 Trigger a login on the account first, then\n"
        "press <b>🔄 Get Live OTP</b> again in ~10 seconds."
    )


# ==================== Support ====================

def format_support() -> str:
    """Support message."""
    return (
        "🆘 <b>Support</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Need help? Contact us:\n\n"
        "📩 <b>Telegram:</b> @KaizenSeller\n"
        "⏰ <b>Response:</b> Within 1 hour\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Have your User ID and Order ID ready."
    )
