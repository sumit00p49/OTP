"""
User middleware - auto-registers users in the database on first interaction.
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from database import get_db


class UserRegistrationMiddleware(BaseMiddleware):
    """Automatically register users in the database on first interaction."""

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        # Extract user from event
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user and not user.is_bot:
            await self._ensure_user_exists(user)

        return await handler(event, data)

    async def _ensure_user_exists(self, user) -> None:
        """Create user in database if not exists."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT user_id, is_banned FROM users WHERE user_id = ?", (user.id,)
        )
        existing = await cursor.fetchone()

        if not existing:
            await db.execute(
                """INSERT INTO users (user_id, username, first_name)
                   VALUES (?, ?, ?)""",
                (user.id, user.username or "", user.first_name or "User"),
            )
            await db.commit()
        else:
            # Update username/first_name if changed
            await db.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                (user.username or "", user.first_name or "User", user.id),
            )
            await db.commit()
