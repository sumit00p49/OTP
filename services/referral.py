"""
Referral system: 5 successful referrals = ₹10 bonus to referrer's wallet.
"""

import logging
from database import get_db
from services.wallet import credit

logger = logging.getLogger(__name__)

REFERRALS_NEEDED = 5
REFERRAL_BONUS = 10.0  # INR


async def process_referral(referrer_id: int, new_user_id: int) -> bool:
    """
    Record a referral. If referrer hits 5 referrals, give ₹10 bonus.
    Returns True if bonus was awarded.
    """
    db = await get_db()

    # Check if already referred
    cur = await db.execute(
        "SELECT id FROM referrals WHERE referred_id = ?", (new_user_id,)
    )
    if await cur.fetchone():
        return False  # Already referred

    # Check referrer exists and isn't the same person
    if referrer_id == new_user_id:
        return False

    cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
    if not await cur.fetchone():
        return False

    # Record referral
    await db.execute(
        "INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
        (referrer_id, new_user_id),
    )
    await db.execute(
        "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
        (referrer_id,),
    )
    await db.execute(
        "UPDATE users SET referred_by = ? WHERE user_id = ?",
        (referrer_id, new_user_id),
    )
    await db.commit()

    # Check if referrer hit the milestone (every 5 referrals = bonus)
    cur = await db.execute(
        "SELECT referral_count FROM users WHERE user_id = ?", (referrer_id,)
    )
    row = await cur.fetchone()
    count = row[0] if row else 0

    if count > 0 and count % REFERRALS_NEEDED == 0:
        await credit(referrer_id, REFERRAL_BONUS)
        logger.info("Referral bonus ₹%.0f awarded to %s (count=%d)", REFERRAL_BONUS, referrer_id, count)
        return True

    return False


async def get_referral_count(user_id: int) -> int:
    """Get total referral count for a user."""
    db = await get_db()
    cur = await db.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    return row[0] if row else 0


def get_referral_link(bot_username: str, user_id: int) -> str:
    """Generate referral link."""
    return f"https://t.me/{bot_username}?start=ref_{user_id}"
