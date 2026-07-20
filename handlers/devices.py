"""
Handler for device/session management on purchased Telegram accounts.

Features:
  - 📱 Devices: Show all active sessions/devices on the account
  - ❌ Remove: User can remove a SPECIFIC device (not all)
  - 🔄 Reset All: Option to terminate ALL sessions at once

Uses LZT API:
  - GET /{item_id}/telegram-active-sessions
  - POST /{item_id}/telegram-reset-auth (with hash = single, without = all)
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
    """
    Fetch and display active sessions/devices.
    Each device has its own ❌ Remove button so user can remove individually.
    """
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
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}"))
        b.row(InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main"))
        await callback.message.answer(msg, reply_markup=b.as_markup(), parse_mode="HTML")
        return

    # Build message with device list
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

        msg += f"{is_current} <b>#{i} {device}</b>"
        if platform:
            msg += f" ({platform})"
        msg += "\n"
        if app:
            msg += f"   📲 {app}\n"
        if ip:
            msg += f"   🌐 {ip}"
            if location:
                msg += f" — {location}"
            msg += "\n"
        elif location:
            msg += f"   📍 {location}\n"
        if active:
            msg += f"   🕐 {active}\n"
        msg += "\n"

    msg += (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ Tap a device below to <b>remove only that device</b>.\n"
        "🔄 Or reset ALL at once."
    )

    # Build keyboard — each device gets its own ❌ Remove button
    b = InlineKeyboardBuilder()
    for i, s in enumerate(sessions, 1):
        device = s.get("device", "Unknown")
        session_hash = s.get("hash", "")
        is_current = s.get("current", False)

        if is_current:
            # Don't allow removing current session
            b.row(InlineKeyboardButton(
                text=f"🟢 #{i} {device} (Current - can't remove)",
                callback_data="noop",
            ))
        elif session_hash:
            b.row(InlineKeyboardButton(
                text=f"❌ #{i} {device}",
                callback_data=f"rm_device:{item_id}:{session_hash}",
            ))
        else:
            # No hash available — can't remove individually
            b.row(InlineKeyboardButton(
                text=f"⚪ #{i} {device} (no hash)",
                callback_data="noop",
            ))

    # Reset ALL button
    b.row(InlineKeyboardButton(
        text="🔄 Reset ALL Sessions",
        callback_data=f"reset_sessions:{item_id}",
    ))
    b.row(InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main"))

    await callback.message.answer(msg, reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Do nothing — for buttons that can't be clicked."""
    await callback.answer("ℹ️ This session can't be removed.", show_alert=False)


@router.callback_query(F.data.startswith("rm_device:"))
async def remove_single_device(callback: CallbackQuery):
    """
    Remove a SINGLE specific device/session.
    Only that one device is logged out, others remain.
    """
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("❌ Invalid", show_alert=True)
        return

    item_id = parts[1]
    session_hash = parts[2]

    await callback.answer("🔄 Removing device...")

    try:
        success = await lzt_api.terminate_single_session(item_id, session_hash)
    except Exception as e:
        logger.warning("Remove single device failed: item=%s hash=%s err=%s", item_id, session_hash, e)
        success = False

    if success:
        await callback.message.answer(
            "✅ <b>Device Removed!</b>\n\n"
            "That session has been terminated.\n"
            "💡 Press <b>📱 Devices</b> to see updated list.",
            reply_markup=_device_refresh_keyboard(item_id),
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(
            "⚠️ <b>Remove Failed</b>\n\n"
            "Could not remove that device.\n"
            "💡 Try <b>🔄 Reset ALL</b> instead.",
            reply_markup=_device_refresh_keyboard(item_id),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("reset_sessions:"))
async def reset_all_sessions(callback: CallbackQuery):
    """Terminate ALL other sessions on the purchased account."""
    item_id = callback.data.replace("reset_sessions:", "")
    if not item_id:
        await callback.answer("❌ Invalid account", show_alert=True)
        return

    await callback.answer("🔄 Terminating all sessions...")

    try:
        success = await lzt_api.terminate_all_sessions(item_id)
    except Exception as e:
        logger.warning("Reset all sessions failed for item %s: %s", item_id, e)
        success = False

    if success:
        msg = (
            "✅ <b>All Sessions Reset!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔄 All other devices have been logged out.\n"
            "The account is now fully under your control.\n\n"
            "🔑 Use <b>Get OTP</b> to login fresh."
        )
    else:
        msg = (
            "⚠️ <b>Reset Failed</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Could not terminate sessions.\n\n"
            "💡 Try again or contact support."
        )

    await callback.message.answer(
        msg,
        reply_markup=_device_refresh_keyboard(item_id),
        parse_mode="HTML",
    )


def _device_refresh_keyboard(item_id: str):
    """Keyboard after device action — refresh list, OTP, back."""
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📱 Refresh Devices", callback_data=f"devices:{item_id}"))
    b.row(InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main"))
    return b.as_markup()
