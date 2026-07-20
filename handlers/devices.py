"""
Handler for device/session management on purchased Telegram accounts.

Features:
  - 📱 Devices: Show all active sessions/devices logged into the account
  - 🔄 Reset Sessions: Terminate all other sessions (kick all devices)

Uses LZT API:
  - GET /{item_id}/telegram-active-sessions
  - POST /{item_id}/telegram-reset-auth
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.lzt_api import lzt_api, LZTAPIError
from keyboards.inline import back_to_main_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("devices:"))
async def show_devices(callback: CallbackQuery):
    """Fetch and display active sessions/devices for a purchased account."""
    item_id = callback.data.replace("devices:", "")
    if not item_id:
        await callback.answer("❌ Invalid account", show_alert=True)
        return

    await callback.answer("🔄 Fetching active devices...")

    try:
        sessions = await lzt_api.get_telegram_active_sessions(item_id)
    except Exception as e:
        logger.warning("Devices fetch failed for item %s: %s", item_id, e)
        sessions = []

    if not sessions:
        msg = (
            "📱 <b>Active Devices</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📭 No active sessions found.\n\n"
            "💡 This could mean:\n"
            "• All sessions were already terminated\n"
            "• The account hasn't been logged in yet\n"
            "• API doesn't support session listing for this account"
        )
    else:
        msg = (
            f"📱 <b>Active Devices ({len(sessions)})</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        for i, s in enumerate(sessions, 1):
            device = s.get("device", "Unknown")
            platform = s.get("platform", "")
            app = s.get("app", "")
            ip = s.get("ip", "")
            location = s.get("location", "")
            active = s.get("active", "")
            is_current = "🟢" if s.get("current") else "⚪"

            msg += f"{is_current} <b>#{i} {device}</b>\n"
            if platform:
                msg += f"   💻 Platform: {platform}\n"
            if app:
                msg += f"   📲 App: {app}\n"
            if ip:
                msg += f"   🌐 IP: {ip}\n"
            if location:
                msg += f"   📍 Location: {location}\n"
            if active:
                msg += f"   🕐 Last Active: {active}\n"
            msg += "\n"

        msg += (
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 Press <b>🔄 Reset Sessions</b> to kick all devices."
        )

    # Build keyboard
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🔄 Reset All Sessions", callback_data=f"reset_sessions:{item_id}")
    )
    b.row(
        InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}")
    )
    b.row(
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")
    )

    await callback.message.answer(msg, reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("reset_sessions:"))
async def reset_sessions(callback: CallbackQuery):
    """Terminate all other sessions on the purchased account."""
    item_id = callback.data.replace("reset_sessions:", "")
    if not item_id:
        await callback.answer("❌ Invalid account", show_alert=True)
        return

    await callback.answer("🔄 Terminating all sessions...")

    try:
        success = await lzt_api.terminate_all_sessions(item_id)
    except Exception as e:
        logger.warning("Reset sessions failed for item %s: %s", item_id, e)
        success = False

    if success:
        msg = (
            "✅ <b>Sessions Reset!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔄 All other devices have been logged out.\n"
            "Only your current session remains active.\n\n"
            "💡 The account is now fully under your control.\n"
            "🔑 Use <b>Get OTP</b> to login fresh."
        )
    else:
        msg = (
            "⚠️ <b>Reset Failed</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Could not terminate sessions.\n\n"
            "💡 Possible reasons:\n"
            "• Account doesn't support this feature\n"
            "• API temporarily unavailable\n"
            "• No active sessions to terminate\n\n"
            "Try again or contact support."
        )

    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📱 Check Devices", callback_data=f"devices:{item_id}")
    )
    b.row(
        InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}")
    )
    b.row(
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")
    )

    await callback.message.answer(msg, reply_markup=b.as_markup(), parse_mode="HTML")
