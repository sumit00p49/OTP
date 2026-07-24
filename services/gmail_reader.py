"""
Gmail reader (IMAP) — reads FamApp/UPI payment notification emails.

Connects to Gmail via IMAP using an App Password (no OAuth needed).
Parses "You received ₹X in your FamX account" emails to extract:
  - amount (with paise, e.g. 100.37)
  - UTR (unique transaction reference)
  - sender name
  - transaction id

Used by auto_payment.py to auto-verify deposits.
"""

import imaplib
import email
import re
import logging
from email.header import decode_header
from datetime import datetime, timedelta

from config import (
    GMAIL_ADDRESS,
    GMAIL_APP_PASSWORD,
    PAYMENT_EMAIL_SENDER,
)

logger = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993


def _decode(value) -> str:
    """Decode an email header value to a plain string."""
    if not value:
        return ""
    parts = decode_header(value)
    out = ""
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out += text.decode(enc or "utf-8", errors="ignore")
            except Exception:
                out += text.decode("utf-8", errors="ignore")
        else:
            out += str(text)
    return out


def _get_body(msg) -> str:
    """Extract the text body from an email.message.Message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" in disp:
                continue
            if ctype in ("text/plain", "text/html"):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(errors="ignore")
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors="ignore")
        except Exception:
            body = ""
    # Strip HTML tags for easier regex
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"&nbsp;", " ", body)
    return body


def parse_payment_email(subject: str, body: str) -> dict | None:
    """
    Parse a FamApp 'received' email into structured payment data.

    Returns dict {amount, utr, sender, txn_id} or None if not a received-payment email.
    """
    text = f"{subject}\n{body}"

    # Only care about RECEIVED payments (incoming money)
    if "received" not in text.lower():
        return None

    # Amount: "received ₹120.0" or "₹120.37"
    amount = None
    m = re.search(r"received\s*[₹Rs.]*\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"[₹]\s*([\d,]+\.\d{1,2})", text)
    if m:
        try:
            amount = float(m.group(1).replace(",", ""))
        except ValueError:
            amount = None

    # UTR: "UTR : 609922866023"
    utr = ""
    m = re.search(r"UTR\s*[:\-]?\s*(\d{6,})", text, re.IGNORECASE)
    if m:
        utr = m.group(1)

    # Transaction ID: "Transaction ID : FMPIB5117307726"
    txn_id = ""
    m = re.search(r"Transaction\s*ID\s*[:\-]?\s*([A-Za-z0-9]+)", text, re.IGNORECASE)
    if m:
        txn_id = m.group(1)

    # Sender: "from BANICHA AHMED"
    sender = ""
    m = re.search(r"from\s+([A-Za-z][A-Za-z .]+?)\s*(?:Transaction|Date|UTR|\n)", text)
    if m:
        sender = m.group(1).strip()

    if amount is None:
        return None

    return {
        "amount": amount,
        "utr": utr,
        "sender": sender,
        "txn_id": txn_id,
        "raw": text,  # full email text — used for note matching
    }


def fetch_recent_payments(since_minutes: int = 30) -> list[dict]:
    """
    Fetch recent payment emails from Gmail via IMAP.

    Returns a list of parsed payment dicts (newest handled by caller).
    Safe: returns [] on any connection/parse error.
    """
    if not (GMAIL_ADDRESS and GMAIL_APP_PASSWORD):
        return []

    payments = []
    imap = None
    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        imap.select("INBOX")

        # Search emails from the payment sender within the time window
        since_date = (datetime.now() - timedelta(minutes=since_minutes + 5)).strftime("%d-%b-%Y")
        # IMAP SINCE is date-granular; we filter finer by parsing later
        criteria = f'(FROM "{PAYMENT_EMAIL_SENDER}" SINCE {since_date})'
        status, data = imap.search(None, criteria)
        if status != "OK" or not data or not data[0]:
            return []

        ids = data[0].split()
        # Only look at the most recent ~20 to stay fast
        for msg_id in ids[-20:]:
            try:
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK" or not msg_data:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = _decode(msg.get("Subject"))
                body = _get_body(msg)
                parsed = parse_payment_email(subject, body)
                if parsed:
                    parsed["msg_id"] = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                    payments.append(parsed)
            except Exception as e:
                logger.debug("Failed to parse one email: %s", e)
                continue

        return payments

    except imaplib.IMAP4.error as e:
        logger.warning("Gmail IMAP login/search failed: %s", e)
        return []
    except Exception as e:
        logger.warning("Gmail fetch error: %s", e)
        return []
    finally:
        if imap is not None:
            try:
                imap.logout()
            except Exception:
                pass


def test_connection() -> tuple[bool, str]:
    """Test the Gmail IMAP connection. Returns (ok, message)."""
    if not (GMAIL_ADDRESS and GMAIL_APP_PASSWORD):
        return False, "GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set in .env"
    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        imap.select("INBOX")
        imap.logout()
        return True, f"Connected to {GMAIL_ADDRESS}"
    except Exception as e:
        return False, f"Connection failed: {e}"
