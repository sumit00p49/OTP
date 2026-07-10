"""
Force Join middleware - user must join a channel before using the bot.
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import FORCE_JOIN_CHANNEL, ADMIN_IDS

logger = logging.getLogger(__name__)


class ForceJoinMiddleware(BaseMiddleware):
    """Check if user has joined the required channel."""

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        # Skip if no channel configured
        if not FORCE_JOIN_CHANNEL:
            return await handler(event, data)

        # Get user
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if not user or user.is_bot:
            return await handler(event, data)

        # Skip for admins
        if user.id in ADMIN_IDS:
            return await handler(event, data)

        # Skip for check_joined callback
        if isinstance(event, CallbackQuery) and event.data == "check_joined":
            return await handler(event, data)

        # Check membership
        try:
            bot = data.get("bot")
            if not bot:
                bot = event.bot if hasattr(event, "bot") else None
            if not bot:
                return await handler(event, data)

            member = await bot.get_chat_member(
                chat_id=f"@{FORCE_JOIN_CHANNEL}", user_id=user.id
            )
            if member.status in ("left", "kicked"):
                await self._send_join_message(event)
                return  # Block handler
        except Exception as e:
            # If check fails (bot not admin in channel), let through
            logger.debug("Force join check failed: %s", e)
            return await handler(event, data)

        return await handler(event, data)

    async def _send_join_message(self, event):
        """Send 'please join' message."""
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(
            text="📢 Join Channel",
            url=f"https://t.me/{FORCE_JOIN_CHANNEL}",
        ))
        b.row(InlineKeyboardButton(text="✅ I Joined", callback_data="check_joined"))
        markup = b.as_markup()

        text = (
            "⚠️ <b>Join Required!</b>\n\n"
            f"Please join @{FORCE_JOIN_CHANNEL} to use this bot.\n\n"
            "After joining, tap <b>✅ I Joined</b> below."
        )

        if isinstance(event, Message):
            await event.answer(text, reply_markup=markup, parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            await event.answer("⚠️ Join the channel first!", show_alert=True)
