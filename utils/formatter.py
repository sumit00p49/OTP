"""
Message formatting utilities for the Telegram OTP Bot.
Provides emoji-rich, well-structured message formatting.
"""


def format_welcome() -> str:
    """Format the welcome message with available commands."""
    return (
        "🤖 <b>Welcome to OTP Now Bot!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Get temporary phone numbers for Telegram & WhatsApp verification.\n\n"
        "📋 <b>Available Commands:</b>\n\n"
        "💰 <b>Account</b>\n"
        "  /balance - Check your balance\n\n"
        "📱 <b>Telegram Numbers</b>\n"
        "  /tg_countries - List available countries\n"
        "  /tg_price [code] - Check price (e.g. /tg_price US)\n"
        "  /tg_order [code] - Order a number (e.g. /tg_order US)\n"
        "  /tg_code [number] - Get OTP code\n\n"
        "💬 <b>WhatsApp Numbers (Server 1)</b>\n"
        "  /wp_countries - List available countries\n"
        "  /wp_price [code] - Check price (e.g. /wp_price IN)\n"
        "  /wp_order [code] - Order a number\n"
        "  /wp_status [order_id] - Check OTP status\n"
        "  /wp_cancel [order_id] - Cancel order & refund\n\n"
        "💬 <b>WhatsApp Numbers (Server 2)</b>\n"
        "  /wp2_countries - List available countries\n"
        "  /wp2_price [code] - Check price\n"
        "  /wp2_order [code] - Order a number\n"
        "  /wp2_status [order_id] - Check OTP status\n"
        "  /wp2_cancel [order_id] - Cancel order & refund\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <i>All operations are real-time via API</i>"
    )


def format_balance(data: dict) -> str:
    """Format balance response."""
    balance = data.get("balance", data.get("amount", "N/A"))
    username = data.get("username", data.get("user", ""))
    email = data.get("email", "")

    msg = "💰 <b>Account Balance</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"

    if username:
        msg += f"👤 User: <code>{username}</code>\n"
    if email:
        msg += f"📧 Email: <code>{email}</code>\n"

    msg += f"💵 Balance: <b>${balance}</b>\n"

    return msg


def format_countries(countries: list | dict, service: str) -> str:
    """
    Format country list response.

    Args:
        countries: List of countries or dict with country data
        service: Service name (Telegram, WhatsApp S1, WhatsApp S2)
    """
    msg = f"🌍 <b>Available Countries - {service}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"

    if isinstance(countries, dict):
        # If response has a data/countries key
        country_list = countries.get("countries", countries.get("data", countries))
        if isinstance(country_list, dict):
            # Format as code: name pairs
            for code, name in country_list.items():
                if isinstance(name, dict):
                    country_name = name.get("name", name.get("country", code))
                    msg += f"  🏳️ <code>{code}</code> - {country_name}\n"
                else:
                    msg += f"  🏳️ <code>{code}</code> - {name}\n"
        elif isinstance(country_list, list):
            for item in country_list:
                if isinstance(item, dict):
                    code = item.get("code", item.get("country_code", "??"))
                    name = item.get("name", item.get("country", code))
                    msg += f"  🏳️ <code>{code}</code> - {name}\n"
                else:
                    msg += f"  🏳️ <code>{item}</code>\n"
    elif isinstance(countries, list):
        for item in countries:
            if isinstance(item, dict):
                code = item.get("code", item.get("country_code", "??"))
                name = item.get("name", item.get("country", code))
                msg += f"  🏳️ <code>{code}</code> - {name}\n"
            else:
                msg += f"  🏳️ <code>{item}</code>\n"

    if not msg.endswith("\n\n"):
        msg += "\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 Use the price command with a country code to check pricing."

    return msg


def format_price(data: dict, country: str, service: str) -> str:
    """
    Format price response.

    Args:
        data: API response data
        country: Country code
        service: Service name
    """
    price = data.get("price", data.get("cost", data.get("amount", "N/A")))
    currency = data.get("currency", "$")
    available = data.get("available", data.get("stock", data.get("count", "")))

    msg = f"💲 <b>Price - {service}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"🌍 Country: <code>{country.upper()}</code>\n"
    msg += f"💵 Price: <b>{currency}{price}</b>\n"

    if available:
        msg += f"📦 Available: <b>{available}</b>\n"

    msg += "\n💡 Use the order command to purchase a number."

    return msg


def format_order(data: dict, service: str) -> str:
    """
    Format order response.

    Args:
        data: API response with order details
        service: Service name
    """
    number = data.get("number", data.get("phone", data.get("phoneNumber", "N/A")))
    order_id = data.get("order_id", data.get("id", data.get("orderId", "")))
    country = data.get("country", data.get("countryCode", ""))
    cost = data.get("cost", data.get("price", ""))

    msg = f"✅ <b>Order Placed - {service}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📱 Number: <code>{number}</code>\n"

    if order_id:
        msg += f"🆔 Order ID: <code>{order_id}</code>\n"
    if country:
        msg += f"🌍 Country: <code>{country}</code>\n"
    if cost:
        msg += f"💵 Cost: <b>${cost}</b>\n"

    msg += "\n⏳ <i>Waiting for OTP code...</i>\n"

    if "tg" in service.lower() or "telegram" in service.lower():
        msg += f"💡 Use /tg_code {number} to check for the code."
    elif "s2" in service.lower() or "server 2" in service.lower():
        if order_id:
            msg += f"💡 Use /wp2_status {order_id} to check OTP status."
        else:
            msg += f"💡 Use /wp2_status with your order ID to check OTP status."
    else:
        if order_id:
            msg += f"💡 Use /wp_status {order_id} to check OTP status."
        else:
            msg += f"💡 Use /wp_status with your order ID to check OTP status."

    return msg


def format_otp_code(data: dict, service: str) -> str:
    """
    Format OTP code response.

    Args:
        data: API response with OTP code
        service: Service name
    """
    code = data.get("code", data.get("otp", data.get("sms", "")))
    number = data.get("number", data.get("phone", ""))
    status = data.get("status", "")

    msg = f"🔑 <b>OTP Code - {service}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"

    if code:
        msg += f"✅ Code: <b><code>{code}</code></b>\n"
        if number:
            msg += f"📱 Number: <code>{number}</code>\n"
        msg += "\n🎉 <i>Use this code to complete verification!</i>"
    else:
        msg += "⏳ <b>OTP not received yet.</b>\n\n"
        msg += "💡 <i>Please wait a moment and try again.</i>\n"
        if status:
            msg += f"📊 Status: {status}"

    return msg


def format_status(data: dict, order_id: str, service: str) -> str:
    """
    Format order status response.

    Args:
        data: API response with status info
        order_id: The order ID checked
        service: Service name
    """
    status = data.get("status", "unknown")
    code = data.get("code", data.get("otp", data.get("sms", "")))
    number = data.get("number", data.get("phone", ""))

    msg = f"📊 <b>Order Status - {service}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"🆔 Order ID: <code>{order_id}</code>\n"

    if number:
        msg += f"📱 Number: <code>{number}</code>\n"

    # Status emoji mapping
    status_emojis = {
        "waiting": "⏳",
        "pending": "⏳",
        "received": "✅",
        "completed": "✅",
        "cancelled": "❌",
        "canceled": "❌",
        "expired": "⏰",
        "error": "⚠️",
    }
    emoji = status_emojis.get(status.lower(), "📋")
    msg += f"{emoji} Status: <b>{status.capitalize()}</b>\n"

    if code:
        msg += f"\n🔑 OTP Code: <b><code>{code}</code></b>\n"
        msg += "\n🎉 <i>Use this code to complete verification!</i>"
    elif status.lower() in ("waiting", "pending"):
        msg += "\n⏳ <i>OTP not received yet. Please wait and check again.</i>"

    return msg


def format_cancel(data: dict, order_id: str, service: str) -> str:
    """
    Format cancel order response.

    Args:
        data: API response
        order_id: The order ID cancelled
        service: Service name
    """
    status = data.get("status", "cancelled")
    refund = data.get("refund", data.get("amount", ""))

    msg = f"❌ <b>Order Cancelled - {service}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"🆔 Order ID: <code>{order_id}</code>\n"
    msg += f"📋 Status: <b>{status.capitalize()}</b>\n"

    if refund:
        msg += f"💵 Refund: <b>${refund}</b>\n"

    msg += "\n✅ <i>Order has been cancelled successfully.</i>"

    return msg


def format_error(error_message: str) -> str:
    """Format an error message."""
    return (
        "⚠️ <b>Error</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❌ {error_message}\n\n"
        "💡 <i>Please try again or check your command.</i>"
    )


def format_usage(command: str, usage: str, example: str) -> str:
    """Format a usage/help message for a command."""
    return (
        f"ℹ️ <b>Usage: {command}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 Format: <code>{usage}</code>\n"
        f"📌 Example: <code>{example}</code>"
    )
