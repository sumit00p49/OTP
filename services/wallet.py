"""
Wallet service - handles all wallet operations.
Credit, debit, and balance checks with atomic transactions.
"""

from database import get_db


async def get_balance(user_id: int) -> float:
    """Get user's current wallet balance."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT wallet_balance FROM users WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if row:
        return float(row[0])
    return 0.0


async def credit(user_id: int, amount: float) -> float:
    """
    Add funds to user's wallet.
    Returns new balance.
    """
    db = await get_db()
    await db.execute(
        "UPDATE users SET wallet_balance = wallet_balance + ? WHERE user_id = ?",
        (amount, user_id),
    )
    await db.commit()
    return await get_balance(user_id)


async def debit(user_id: int, amount: float) -> tuple[bool, float]:
    """
    Deduct funds from user's wallet.
    Returns (success, new_balance).
    Fails if insufficient balance.
    """
    db = await get_db()
    current = await get_balance(user_id)

    if current < amount:
        return False, current

    await db.execute(
        "UPDATE users SET wallet_balance = wallet_balance - ? WHERE user_id = ?",
        (amount, user_id),
    )
    await db.commit()
    new_balance = await get_balance(user_id)
    return True, new_balance


async def has_sufficient_balance(user_id: int, amount: float) -> bool:
    """Check if user has enough balance."""
    balance = await get_balance(user_id)
    return balance >= amount
