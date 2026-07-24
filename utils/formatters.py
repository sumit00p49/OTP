"""
Message formatting helpers with rich emojis.
Simplified for India-only TG Premium accounts at fixed ₹60.
Uses standard Unicode emojis (works without Telegram Premium).
"""

import json


def format_welcome(first_name: str, balance: float) -> str:
    """Format the welcome/start message with premium branding."""
    return (
        f"👋 <b>Welcome, {first_name}!</b>\n"
        "\n"
        "✨ 𝙋𝙧𝙚𝙢𝙞𝙪𝙢 𝙏𝙚𝙡𝙚𝙜𝙧𝙖𝙢 𝙄𝘿𝙨\n"
        "✨ 𝙑𝙞𝙧𝙩𝙪𝙖𝙡 𝙉𝙪𝙢𝙗𝙚𝙧 𝙑𝙚𝙧𝙞𝙛𝙞𝙚𝙙\n"
        "✨ 𝘽𝙪𝙡𝙠 𝙊𝙧𝙙𝙚𝙧 𝙊𝙛𝙛𝙚𝙧𝙨\n"
        "✨ 𝙄𝙣𝙨𝙩𝙖𝙣𝙩 𝘿𝙚𝙡𝙞𝙫𝙚𝙧𝙮\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "    ⚡ 𝟮𝟰/𝟳  •  🔐 𝟭𝟬𝟬% 𝗦𝗮𝗳𝗲\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        f"💳 <b>Balance:</b> ₹{balance:.2f}\n"
        "📦 <b>Status:</b> ✅ Active\n"
    )


def format_buy_country_select() -> str:
    """Country/product selection screen."""
    return (
        "🟢 Fresh Accounts\n"
        "──────────────────────\n"
        "👇 Select a country:"
    )


def format_quantity_select(price_per: float) -> str:
    """Quantity selection screen."""
    return (
        "📱 <b>𝐁𝐮𝐲 𝐓𝐞𝐥𝐞𝐠𝐫𝐚𝐦 𝐀𝐜𝐜𝐨𝐮𝐧𝐭</b>\n"
        "\n"
        f"🇮🇳 INDIAN  —  ₹{price_per:.0f}\n"
        "\n"
        "📦 Select quantity:"
    )


def format_buy_confirm(qty: int, price_per: float, total: float, balance: float, country_label: str = "🇮🇳 India") -> str:
    """Purchase confirmation."""
    return (
        "🛒 <b>Confirm Purchase</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌍 <b>Country:</b> {country_label}\n"
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
    """Format delivered account details with login instructions + rich emojis."""
    phone = account_data.get("phone", "N/A")
    password = account_data.get("password", "")
    username = account_data.get("username", "")
    email = account_data.get("email", "")
    login_code = account_data.get("login_code", "")
    otp_available = account_data.get("otp_available", False)

    msg = (
        "🎉✨ <b>Purchase Successful!</b> ✨🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>Order:</b> <code>{order_id}</code>\n"
        f"📲 <b>Phone:</b> <code>{phone}</code>\n"
    )
    if username:
        msg += f"👤 <b>Username:</b> @{username}\n"
    if email:
        msg += f"📧 <b>Email:</b> <code>{email}</code>\n"
    if password:
        msg += f"🔐 <b>2FA Password:</b> <code>{password}</code>\n"
    if login_code:
        msg += f"🔢 <b>Login Code:</b> <code>{login_code}</code>\n"

    msg += (
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>How to Login:</b>\n"
        "1️⃣ Open Telegram Desktop/Mobile\n"
        "2️⃣ Enter the phone number above\n"
        "3️⃣ Tap <b>🔑 Get OTP</b> below for the code\n"
        "\n"
        "🛡️ <b>Status:</b> ✅ Clean • No Spam Block\n"
        "💚 <b>Full account control is yours!</b>"
    )

    if not otp_available:
        msg += (
            "\n\n"
            "⚠️ <i>Note: If OTP doesn't arrive, this account\n"
            "may need TData login — contact support.</i>"
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
        "No accounts available for this country right now.\n\n"
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
    """Format deposit instructions with small caps styled text."""
    return (
        "💰 ᴅᴇᴘᴏsɪᴛ ғᴜɴᴅs\n"
        "\n"
        "📲 ᴜᴘɪ ɪᴅ: <code>SurojSeller@fam</code>\n"
        f"👤 ɴᴀᴍᴇ: 𝗦𝗔𝗡𝗗𝗜𝗣 𝗕𝗘𝗥𝗔\n"
        "\n"
        "1. sᴇɴᴅ ᴍᴏɴᴇʏ ᴠɪᴀ ᴜᴘɪ\n"
        "2. ᴛᴀᴘ ᴍᴀᴋᴇ ᴅᴇᴘᴏsɪᴛ ᴀɴᴅ ᴇɴᴛᴇʀ ᴀᴍᴏᴜɴᴛ\n"
        "3. ᴜᴘʟᴏᴀᴅ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ\n"
        "4. ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴇs → ʙᴀʟᴀɴᴄᴇ ᴀᴅᴅᴇᴅ 🎉\n"
    )


def format_deposit_amount_prompt() -> str:
    """Prompt for deposit amount - styled italic bold."""
    return (
        "💸 𝙀𝙣𝙩𝙚𝙧 𝘿𝙚𝙥𝙤𝙨𝙞𝙩 𝘼𝙢𝙤𝙪𝙣𝙩 (₹)\n"
        "\n"
        "📝 𝙏𝙮𝙥𝙚 𝙩𝙝𝙚 𝙚𝙭𝙖𝙘𝙩 𝙖𝙢𝙤𝙪𝙣𝙩 𝙮𝙤𝙪 𝙨𝙚𝙣𝙩.\n"
        "📌 𝙀𝙭𝙖𝙢𝙥𝙡𝙚: <code>100</code>\n"
        "\n"
        "⚠️ 𝙈𝙞𝙣𝙞𝙢𝙪𝙢 𝙙𝙚𝙥𝙤𝙨𝙞𝙩: ₹10"
    )


def format_deposit_screenshot_prompt(amount: float) -> str:
    """Deposit details box shown after user enters amount."""
    return (
        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "     💸 𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗗𝗘𝗧𝗔𝗜𝗟𝗦\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n"
        "\n"
        f"  𝗔𝗠𝗢𝗨𝗡𝗧 : <b>₹{amount:.0f}</b>\n"
        "  𝗨𝗣𝗜 𝗜𝗗 : <code>SurojSeller@fam</code>\n"
        "  𝗡𝗔𝗠𝗘   : 𝗦𝗔𝗡𝗗𝗜𝗣 𝗕𝗘𝗥𝗔\n"
        "\n"
        "  📸 𝗦𝗘𝗡𝗗 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧\n"
        "  ✅ 𝗔𝗗𝗠𝗜𝗡 𝗪𝗜𝗟𝗟 𝗔𝗣𝗣𝗥𝗢𝗩𝗘 & 𝗔𝗗𝗗 𝗕𝗔𝗟𝗔𝗡𝗖𝗘\n"
    )


def format_deposit_pending() -> str:
    """Deposit submitted confirmation - styled small caps."""
    return (
        "ᴛʜᴀɴᴋs ғᴏʀ ᴅᴇᴘᴏsɪᴛ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ .\n"
        "\n"
        "ᴏᴜʀ ᴀᴅᴍɪɴs ᴡɪʟʟ sᴏᴏɴ ᴄʜᴇᴄᴋ ᴀɴᴅ ᴀᴘᴘʀᴏᴠᴇ."
    )


def format_auto_deposit_prompt(base_amount: float, note: str, upi_id: str, upi_name: str) -> str:
    """Auto-verify deposit: pay exact amount + add the note (no extra paise)."""
    return (
        "⚡ <b>Instant Auto-Verify Deposit</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 <b>Amount:</b> ₹{base_amount:.0f}\n"
        f"📲 <b>UPI ID:</b> <code>{upi_id}</code>\n"
        f"👤 <b>Name:</b> {upi_name}\n\n"
        "📝 <b>IMPORTANT — Add this NOTE while paying:</b>\n"
        f"➡️ <code>{note}</code>\n"
        "<i>(type it in the 'note/remark/message' box in your UPI app)</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 <b>Auto-verify is ON!</b>\n"
        f"Pay ₹{base_amount:.0f} with the note above — your wallet is\n"
        "credited automatically within ~1 minute.\n\n"
        "⏱️ Pay within 10 minutes."
    )


def format_auto_deposit_waiting() -> str:
    """Shown when user taps 'I've Paid' but payment not detected yet."""
    return (
        "⏳ <b>Waiting for payment...</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "We haven't detected your payment yet.\n\n"
        "💡 <b>Please make sure:</b>\n"
        "• You paid the <b>EXACT</b> amount (with paise)\n"
        "• Payment is complete (not pending)\n\n"
        "🔄 Wait ~1 minute and tap <b>Check Again</b>.\n"
        "It auto-credits as soon as it's detected."
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
        msg += f"💾 TData: Available (contact support)\n"

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
    """Fresh OTP received via API."""
    return (
        "🔑 <b>OTP Received!</b>\n"
        "\n"
        f"📲 Code: <code>{code}</code>\n"
        "\n"
        "💡 Tap the code to copy.\n"
        "Press <b>🔑 Get OTP</b> again for a new code."
    )


def format_otp_not_ready() -> str:
    """No OTP available yet."""
    return (
        "⏳ <b>OTP Not Ready</b>\n"
        "\n"
        "Code hasn't arrived yet.\n"
        "\n"
        "💡 <b>Steps:</b>\n"
        "1. Open Telegram app on another device\n"
        "2. Try to login with the phone number\n"
        "3. Wait 10 seconds\n"
        "4. Press <b>🔑 Get OTP</b> again\n"
        "\n"
        "⚠️ If code still doesn't come, the account\n"
        "may need TData login instead."
    )


# ==================== Support ====================

def format_support() -> str:
    """Support message."""
    return (
        "🆘 <b>Support</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Need help? Tap below to chat:\n\n"
        "📩 <b>Telegram:</b> @OverrMaxx\n"
        "⏰ <b>Response:</b> Within 1 hour\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Have your User ID and Order ID ready."
    )
