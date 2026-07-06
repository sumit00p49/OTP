"""
Order service - handles order creation, retrieval, and management.
"""

import json
import uuid
from typing import Optional
from database import get_db


async def create_order(
    user_id: int,
    lzt_item_id: str,
    amount_paid: float,
    account_data: dict,
    quality: str,
    country: str,
) -> str:
    """
    Create a new order record.

    Returns:
        Generated order_id string
    """
    db = await get_db()
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    await db.execute(
        """INSERT INTO orders (order_id, user_id, lzt_item_id, amount_paid, account_data, quality, country)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            order_id,
            user_id,
            str(lzt_item_id),
            amount_paid,
            json.dumps(account_data),
            quality,
            country,
        ),
    )
    await db.commit()
    return order_id


async def get_order(order_id: str) -> Optional[dict]:
    """Get a specific order by order_id."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id,)
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return None


async def get_user_orders(user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
    """Get all orders for a user, most recent first."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM orders WHERE user_id = ?
           ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        (user_id, limit, offset),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_user_order_count(user_id: int) -> int:
    """Get total order count for a user."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def get_order_details(order_id: str) -> Optional[dict]:
    """Get order with parsed account data."""
    order = await get_order(order_id)
    if order and order.get("account_data"):
        try:
            order["account_data_parsed"] = json.loads(order["account_data"])
        except (json.JSONDecodeError, TypeError):
            order["account_data_parsed"] = {}
    return order
