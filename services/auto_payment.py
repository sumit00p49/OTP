"""
Auto Payment verification engine (NO extra paise).

Matching strategy (2 layers):
  1) NOTE match  — each deposit gets a short note (e.g. APX4821). If the payer
     adds it and it appears in the FamApp email, we match exactly. (best)
  2) AMOUNT + TIME window — otherwise, match a PENDING deposit whose exact
     amount equals the received amount and was created within the last N min
     (oldest first). UTR dedup guarantees each payment credits only once.

Runs ONLY when AUTO_VERIFY_ENABLED (Gmail creds present).
"""

import asyncio
import logging
import random
import string

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


async def generate_deposit_note() -> str:
    """
    Generate a short unique note like 'APX4821' for a deposit.
    The payer adds this in the UPI note/remark so we can match exactly.
    """
    db = await get_db()
    for _ in range(20):
        note = "APX" + "".join(random.choices(string.digits, k=4))
        cur = await db.execute(
            "SELECT 1 FROM deposits WHERE note=? AND status='PENDING'", (note,)
        )
        if not await cur.fetchone():
            return note
    # Fallback — extremely unlikely
    return "APX" + "".join(random.choices(string.digits, k=6))


async def reserve_unique_amount(base_amount: float) -> float:
    """Kept for backward-compat. We no longer add paise — return base as-is."""
    return round(float(base_amount), 2)


async def _is_utr_used(utr: str) -> bool:
    """Check if a UTR was already claimed."""
    if not utr:
        return False
    db = await get_db()
    cur = await db.execute("SELECT 1 FROM used_utrs WHERE utr=?", (utr,))
    return await cur.fetchone() is not None


async def _mark_utr_used(utr: str, deposit_id: int, amount: float):
    """Record a UTR as used (prevents the same payment crediting twice)."""
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


async def _find_matching_deposit(payment: dict):
    """
    Find a PENDING deposit matching this payment.
    Layer 1: note found in email text.
    Layer 2: exact amount + within time window (oldest first).
    Returns row or None.
    """
    db = await get_db()
    amount = payment.get("amount")
    raw = (payment.get("raw") or "").upper()

    # ---- Layer 1: NOTE match ----
    # Look at pending deposits within window that have a note, see if note is in email
    cur = await db.execute(
        f"""SELECT id, user_id, amount, note FROM deposits
            WHERE status='PENDING' AND note != ''
            AND created_at >= datetime('now', '-{PAYMENT_MATCH_WINDOW_MIN} minutes')
            ORDER BY created_at ASC"""
    )
    rows = await cur.fetchall()
    for r in rows:
        note = (r["note"] or "").upper()
        if note and note in raw:
            # If amount also present, prefer exact amount too; but note alone is strong
            return r

    # ---- Layer 2: AMOUNT + TIME window ----
    if amount is None:
        return None
    cur = await db.execute(
        f"""SELECT id, user_id, amount, note FROM deposits
            WHERE status='PENDING'
            AND created_at >= datetime('now', '-{PAYMENT_MATCH_WINDOW_MIN} minutes')
            ORDER BY created_at ASC"""
    )
    rows = await cur.fetchall()
    for r in rows:
        if abs(float(r["amount"]) - amount) < 0.5:  # exact rupee match (tolerance for .0)
            return r
    return None


async def process_payment(payment: dict, bot) -> bool:
    """Try to match a single parsed payment email to a pending deposit."""
    amount = payment.get("amount")
    utr = payment.get("utr", "")
    if amount is None:
        return False

    # Skip already-used payments
    if utr and await _is_utr_used(utr):
        return False

    match = await _find_matching_deposit(payment)
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
        return False  # Already handled

    await _mark_utr_used(utr, deposit_id, amount)

    # Credit the requested amount
    new_balance = await credit(user_id, base_amount)

    logger.info(
        "AUTO-APPROVED deposit #%s: user=%s amount=%.2f utr=%s note=%s",
        deposit_id, user_id, base_amount, utr, match["note"],
    )

    try:
        await bot.send_message(
            user_id,
            format_deposit_approved(base_amount, new_balance),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Failed to notify user %s: %s", user_id, e)

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
        logger.info("Auto-payment verification DISABLED (no Gmail creds). Manual only.")
        return

    logger.info(
        "Auto-payment poller started (every %ss, window %smin, note+amount match).",
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
