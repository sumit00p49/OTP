"""
Handler for device/session management on purchased Telegram accounts.

Features:
  - 📱 Manage Sessions: Show all active devices on the account
  - ❌ Remove: User picks WHICH device to remove (only that one logs out)
  - Current session (user's own) is protected — can't be removed

Uses LZT API:
  - GET /{item_id}/telegram-active-sessions
  - POST /{item_id}/telegram-reset-auth with hash (removes single session)

IMPORTANT: We NEVER reset ALL sessions because that would log the user out too!
Only individual device removal is allowed.
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
    Each non-current device has ❌ Remove button.
    User picks which one to remove — only that device gets logged out.
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
            "📱 <b>Active Sessions</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📭 No active sessions found.\n\n"
            "💡 This means:\n"
            "• No other device is logged in\n"
            "• The account is clean — only you can login\n\n"
            "🔑 Use <b>Get OTP</b> to login now."
        )
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}"))
        b.row(InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main"))
        await callback.message.answer(msg, reply_markup=b.as_markup(), parse_mode="HTML")
        return

    # Build message with device list
    msg = (
        f"📱 <b>Active Sessions ({len(sessions)})</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    for i, s in enumerate(sessions, 1):
        device = s.get("device", "Unknown")
        platform = s.get("platform", "")
        app = s.get("app", "")
        ip = s.get("ip", "")
        location = s.get("location", "")
        active = s.get("active", "")
        is_current = s.get("current", False)

        icon = "🟢" if is_current else "⚪"
        msg += f"{icon} <b>#{i} {device}</b>"
        if platform:
            msg += f" ({platform})"
        if is_current:
            msg += " ← Your session"
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
        "👇 <b>Tap ❌ to remove that device only.</b>\n"
        "Your own session won't be affected."
    )

    # Build keyboard — each device gets its own ❌ Remove button
    b = InlineKeyboardBuilder()
    for i, s in enumerate(sessions, 1):
        device = s.get("device", "Unknown")
        session_hash = s.get("hash", "")
        is_current = s.get("current", False)

        if is_current:
            # User's own session — protected, can't remove
            b.row(InlineKeyboardButton(
                text=f"🟢 #{i} {device} (Your session ✓)",
                callback_data="noop",
            ))
        elif session_hash:
            # Other device — can be removed
            b.row(InlineKeyboardButton(
                text=f"❌ Remove #{i} {device}",
                callback_data=f"rm_device:{item_id}:{session_hash}",
            ))
        else:
            b.row(InlineKeyboardButton(
                text=f"⚪ #{i} {device}",
                callback_data="noop",
            ))

    b.row(InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main"))

    await callback.message.answer(msg, reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Do nothing — for protected sessions."""
    await callback.answer("✅ This is your session — safe!", show_alert=False)


@router.callback_query(F.data.startswith("rm_device:"))
async def remove_single_device(callback: CallbackQuery):
    """
    Remove a SINGLE specific device/session.
    Only that one device is logged out. User's session stays active.
    """
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("❌ Invalid", show_alert=True)
        return

    item_id = parts[1]
    session_hash = parts[2]

    await callback.answer("🔄 Removing that device...")

    try:
        success = await lzt_api.terminate_single_session(item_id, session_hash)
    except Exception as e:
        logger.warning("Remove single device failed: item=%s hash=%s err=%s", item_id, session_hash, e)
        success = False

    if success:
        await callback.message.answer(
            "✅ <b>Device Removed!</b>\n\n"
            "That device has been logged out.\n"
            "Your session is still active ✓\n\n"
            "💡 Press <b>📱 Manage Sessions</b> to see updated list.",
            reply_markup=_device_refresh_keyboard(item_id),
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(
            "⚠️ <b>Remove Failed</b>\n\n"
            "Could not remove that device.\n"
            "It may have already been logged out.\n\n"
            "💡 Press 📱 to refresh the list.",
            reply_markup=_device_refresh_keyboard(item_id),
            parse_mode="HTML",
        )


# Remove the old reset_sessions handler — we don't want bulk reset
@router.callback_query(F.data.startswith("reset_sessions:"))
async def reset_sessions_redirect(callback: CallbackQuery):
    """Redirect old reset_sessions to device list instead of bulk reset."""
    item_id = callback.data.replace("reset_sessions:", "")
    # Instead of resetting all, show device list so user can pick individually
    callback.data = f"devices:{item_id}"
    await show_devices(callback)


def _device_refresh_keyboard(item_id: str):
    """Keyboard after device action — refresh list, OTP, back."""
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📱 Manage Sessions", callback_data=f"devices:{item_id}"))
    b.row(InlineKeyboardButton(text="🔑 Get OTP", callback_data=f"get_otp:{item_id}"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main"))
    return b.as_markup()
