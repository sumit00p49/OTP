"""
Daily report - sends admin a summary every day.
"""

import logging
from datetime import date
from database import get_db
from config import ADMIN_IDS

logger = logging.getLogger(__name__)


async def generate_daily_report() -> str:
    """Generate today's report text."""
    db = await get_db()
    today = date.today().isoformat()

    # Deposits
    cur = await db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM deposits WHERE status='APPROVED' AND DATE(created_at)=?",
        (today,),
    )
    dep = await cur.fetchone()

    # Orders/Sales
    cur = await db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount_paid),0) FROM orders WHERE DATE(created_at)=?",
        (today,),
    )
    ords = await cur.fetchone()

    # New users today
    cur = await db.execute(
        "SELECT COUNT(*) FROM users WHERE DATE(created_at)=?", (today,)
    )
    new_users = (await cur.fetchone())[0]

    # Pending deposits
    cur = await db.execute("SELECT COUNT(*) FROM deposits WHERE status='PENDING'")
    pending = (await cur.fetchone())[0]

    # Total users
    cur = await db.execute("SELECT COUNT(*) FROM users")
    total_users = (await cur.fetchone())[0]

    return (
        f"📊 <b>Daily Report — {today}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛒 <b>Sales:</b> {ords[0]} orders (₹{ords[1]:.0f})\n"
        f"💰 <b>Deposits:</b> {dep[0]} approved (₹{dep[1]:.0f})\n"
        f"👥 <b>New Users:</b> {new_users}\n"
        f"⏳ <b>Pending:</b> {pending} deposits\n"
        f"📈 <b>Total Users:</b> {total_users}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Revenue:</b> ₹{ords[1]:.0f}"
    )


async def send_daily_report(bot):
    """Send daily report to all admins."""
    report = await generate_daily_report()
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, report, parse_mode="HTML")
        except Exception as e:
            logger.warning("Failed to send daily report to %s: %s", admin_id, e)
