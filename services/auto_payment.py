"""
Auto Payment verification engine.

Flow:
  - When a user starts a deposit, we reserve a UNIQUE amount (base + unique paise)
    so each pending payment can be matched by its exact rupee value.
  - A background poller reads Gmail every N seconds, parses received-payment
    emails, and matches them to pending deposits by exact amount.
  - On match: credit the user's wallet, mark deposit APPROVED, store the UTR
    (so the same payment can never be reused), and notify the user.

This runs ONLY when AUTO_VERIFY_ENABLED (Gmail creds present).
"""

import asyncio
import logging
import random

from config import (
    AUTO_VERIFY_ENABLED,
    PAYMENT_POLL_INTERVAL,
    PAYMENT_MATCH_WINDOW_MIN,
)
from database import get_db
from services.wallet import credit
from services.gmail_reader import fetch_recent_payments
from utils.formatters import format_deposit_approved

logger = logging.getLogger(__name__)


async def reserve_unique_amount(base_amount: float) -> float:
    """
    Given a base deposit amount, return a UNIQUE amount by appending paise
    that no other PENDING deposit is currently using.

    e.g. base 100 -> 100.37 (if .37 not already pending)
    """
    db = await get_db()
    # Collect paise already used by pending deposits with same base
    cur = await db.execute(
        "SELECT unique_amount FROM deposits WHERE status='PENDING' AND unique_amount > 0"
    )
    rows = await cur.fetchall()
    used_paise = set()
    for r in rows:
        val = r[0]
        if val:
            paise = round((val - int(val)) * 100)
            used_paise.add(paise)

    # Pick a random unused paise between 1 and 99
    choices = [p for p in range(1, 100) if p not in used_paise]
    if not choices:
        # Extremely unlikely (99 concurrent pending) — fall back to base
        return round(base_amount + 0.01, 2)

    paise = random.choice(choices)
    return round(int(base_amount) + paise / 100.0, 2)


async def _is_utr_used(utr: str) -> bool:
    """Check if a UTR was already claimed."""
    if not utr:
        return False
    db = await get_db()
    cur = await db.execute("SELECT 1 FROM used_utrs WHERE utr=?", (utr,))
    return await cur.fetchone() is not None


async def _mark_utr_used(utr: str, deposit_id: int, amount: float):
    """Record a UTR as used."""
    if not utr:
        return
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO used_utrs (utr, deposit_id, amount) VALUES (?, ?, ?)",
            (utr, deposit_id, amount),
        )
        await db.commit()
    except Exception as e:
        logger.warning("Failed to record UTR %s: %s", utr, e)


async def _find_matching_deposit(amount: float):
    """
    Find a PENDING deposit whose unique_amount matches the received amount
    within the time window.
    Returns row dict or None.
    """
    db = await get_db()
    cur = await db.execute(
        f"""SELECT id, user_id, amount, unique_amount FROM deposits
            WHERE status='PENDING' AND unique_amount > 0
            AND created_at >= datetime('now', '-{PAYMENT_MATCH_WINDOW_MIN} minutes')
            ORDER BY created_at ASC"""
    )
    rows = await cur.fetchall()
    for r in rows:
        # Match exact amount (allow tiny float tolerance)
        if abs(float(r["unique_amount"]) - amount) < 0.005:
            return r
    return None


async def process_payment(payment: dict, bot) -> bool:
    """
    Try to match a single parsed payment email to a pending deposit.
    Returns True if a deposit was auto-approved.
    """
    amount = payment.get("amount")
    utr = payment.get("utr", "")
    if amount is None:
        return False

    # Skip already-used payments
    if utr and await _is_utr_used(utr):
        return False

    match = await _find_matching_deposit(amount)
    if not match:
        return False

    deposit_id = match["id"]
    user_id = match["user_id"]
    base_amount = float(match["amount"])

    db = await get_db()
    # Atomically approve only if still pending
    cur = await db.execute(
        "UPDATE deposits SET status='APPROVED', utr=?, verify_method='auto' "
        "WHERE id=? AND status='PENDING'",
        (utr, deposit_id),
    )
    await db.commit()
    if cur.rowcount == 0:
        return False  # Already handled by someone else

    await _mark_utr_used(utr, deposit_id, amount)

    # Credit the user's wallet with the base amount they requested
    new_balance = await credit(user_id, base_amount)

    logger.info(
        "AUTO-APPROVED deposit #%s: user=%s amount=%.2f (paid %.2f) utr=%s",
        deposit_id, user_id, base_amount, amount, utr,
    )

    # Notify the user
    try:
        await bot.send_message(
            user_id,
            format_deposit_approved(base_amount, new_balance),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Failed to notify user %s of auto-approval: %s", user_id, e)

    return True


async def poll_once(bot) -> int:
    """Run one polling cycle. Returns number of deposits auto-approved."""
    payments = await asyncio.to_thread(fetch_recent_payments, PAYMENT_MATCH_WINDOW_MIN)
    if not payments:
        return 0
    approved = 0
    for p in payments:
        try:
            if await process_payment(p, bot):
                approved += 1
        except Exception as e:
            logger.warning("Error processing payment %s: %s", p, e)
    return approved


async def payment_poller(bot):
    """Background task: continuously poll Gmail for payments."""
    if not AUTO_VERIFY_ENABLED:
        logger.info("Auto-payment verification DISABLED (no Gmail creds). Manual approval only.")
        return

    logger.info(
        "Auto-payment poller started (every %ss, window %smin).",
        PAYMENT_POLL_INTERVAL, PAYMENT_MATCH_WINDOW_MIN,
    )
    while True:
        try:
            n = await poll_once(bot)
            if n:
                logger.info("Auto-approved %d deposit(s) this cycle.", n)
        except Exception as e:
            logger.warning("Payment poller cycle error: %s", e)
        await asyncio.sleep(PAYMENT_POLL_INTERVAL)
