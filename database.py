"""
Database module - SQLite setup and connection management.
Creates tables: users, deposits, orders.
"""

import aiosqlite
from config import DB_PATH

_db_connection = None


async def get_db() -> aiosqlite.Connection:
    """Get or create database connection."""
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(DB_PATH)
        _db_connection.row_factory = aiosqlite.Row
        await _db_connection.execute("PRAGMA journal_mode=WAL")
        await _db_connection.execute("PRAGMA foreign_keys=ON")
    return _db_connection


async def init_db():
    """Initialize database and create tables."""
    db = await get_db()

    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            wallet_balance REAL DEFAULT 0.00,
            referred_by INTEGER DEFAULT 0,
            referral_count INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            screenshot_file_id TEXT,
            status TEXT DEFAULT 'PENDING',
            admin_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            lzt_item_id TEXT,
            amount_paid REAL NOT NULL,
            account_data TEXT,
            quality TEXT,
            country TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: add new columns if they don't exist (for existing databases)
    try:
        await db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'en'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE orders ADD COLUMN rating TEXT DEFAULT ''")
    except Exception:
        pass

    # Auto-payment verification columns on deposits
    try:
        await db.execute("ALTER TABLE deposits ADD COLUMN unique_amount REAL DEFAULT 0")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE deposits ADD COLUMN utr TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE deposits ADD COLUMN verify_method TEXT DEFAULT 'manual'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE deposits ADD COLUMN note TEXT DEFAULT ''")
    except Exception:
        pass

    # Track used UTRs so the same payment can't be claimed twice
    await db.execute("""
        CREATE TABLE IF NOT EXISTS used_utrs (
            utr TEXT PRIMARY KEY,
            deposit_id INTEGER,
            amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.commit()


async def close_db():
    """Close database connection."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
