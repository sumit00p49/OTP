"""
Product Manager — countries/products stored in SQLite (same DB as users/orders).

No products.json file, no MongoDB. Everything is managed via the bot admin
panel (Add / Remove / Edit Price / Edit Max LZT). Countries persist across
restarts and git pulls, and can never break from JSON typos.

DEFAULT FILTERS (auto-applied to EVERY country search):
  - nsb=1        (No Spam Block)
  - spam=no      (No Spam Block)
  - email=yes    (Email/Gmail linked)
These match the tested lzt.market filter: "Spam block: No, Email linked".
Per-country extra filters (in the 'filters' column) merge on top.
"""

import sqlite3
import json
import os
import logging
from typing import Optional

from config import DB_PATH

logger = logging.getLogger(__name__)

# Filters applied to every country automatically
GLOBAL_DEFAULT_FILTERS = {
    "nsb": 1,
    "spam": "no",
    "email": "yes",
}

# Seed data used ONLY the first time (empty DB and no products.json to migrate).
# After the first run the DB is the single source of truth — manage countries
# via the bot admin panel. products.json is only a one-time seed.
DEFAULT_PRODUCTS = [
    {"code": "IN", "name": "India", "flag": "\U0001f1ee\U0001f1f3", "price": 26, "max_lzt": 0.20, "filters": {}},
    {"code": "US", "name": "United States", "flag": "\U0001f1fa\U0001f1f8", "price": 50, "max_lzt": 0.30, "filters": {}},
    {"code": "BD", "name": "Bangladesh", "flag": "\U0001f1e7\U0001f1e9", "price": 20, "max_lzt": 0.18, "filters": {}},
    {"code": "ID", "name": "Indonesia", "flag": "\U0001f1ee\U0001f1e9", "price": 25, "max_lzt": 0.18, "filters": {}},
    {"code": "MM", "name": "Myanmar", "flag": "\U0001f1f2\U0001f1f2", "price": 22, "max_lzt": 0.18, "filters": {}},
    {"code": "VN", "name": "Vietnam", "flag": "\U0001f1fb\U0001f1f3", "price": 30, "max_lzt": 0.18, "filters": {}},
    {"code": "PK", "name": "Pakistan", "flag": "\U0001f1f5\U0001f1f0", "price": 30, "max_lzt": 0.18, "filters": {}},
]

_LEGACY_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "products.json"
)


def _conn() -> sqlite3.Connection:
    """Open a short-lived sync SQLite connection (WAL-safe alongside aiosqlite)."""
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def _row_to_dict(row) -> dict:
    """Convert a products row to the dict shape the rest of the bot expects."""
    try:
        filters = json.loads(row["filters"]) if row["filters"] else {}
    except (json.JSONDecodeError, TypeError):
        filters = {}
    return {
        "code": row["code"],
        "name": row["name"],
        "flag": row["flag"],
        "price": row["price"],
        "max_lzt": row["max_lzt"],
        "filters": filters if isinstance(filters, dict) else {},
    }



def init_products():
    """
    Create the products table if missing and seed it once.
    Seeds from an existing products.json (migration) or DEFAULT_PRODUCTS.
    Safe to call every startup — only seeds when the table is empty.
    """
    conn = _conn()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS products (
                code       TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                flag       TEXT DEFAULT '',
                price      REAL NOT NULL,
                max_lzt    REAL NOT NULL,
                filters    TEXT DEFAULT '{}',
                sort_order INTEGER DEFAULT 0
            )"""
        )
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            seed = _load_legacy_json() or DEFAULT_PRODUCTS
            for i, p in enumerate(seed):
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO products "
                        "(code, name, flag, price, max_lzt, filters, sort_order) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            str(p["code"]).upper(), p.get("name", p["code"]),
                            p.get("flag", "\U0001f30d"), float(p.get("price", 0)),
                            float(p.get("max_lzt", 0.15)),
                            json.dumps(p.get("filters", {})), i,
                        ),
                    )
                except Exception as e:
                    logger.warning("Seed product %s failed: %s", p.get("code"), e)
            conn.commit()
            logger.info("Seeded %d products into DB.", len(seed))
    finally:
        conn.close()


def _load_legacy_json() -> list:
    """One-time migration source: read products.json if it exists."""
    if os.path.exists(_LEGACY_JSON):
        try:
            with open(_LEGACY_JSON, "r") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                logger.info("Migrating %d products from products.json to DB.", len(data))
                return data
        except Exception as e:
            logger.warning("Could not read legacy products.json: %s", e)
    return []


# ==================== Read ====================

def get_all_products() -> list:
    """All products, ordered."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY sort_order, code"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def get_product(code: str) -> Optional[dict]:
    """One product by country code, or None."""
    conn = _conn()
    try:
        r = conn.execute(
            "SELECT * FROM products WHERE code = ?", (code.upper(),)
        ).fetchone()
        return _row_to_dict(r) if r else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()



# ==================== Write ====================

def add_product(code: str, name: str, flag: str, price: float, max_lzt: float, filters: dict) -> bool:
    """Add a new country. Returns False if it already exists."""
    code = code.upper()
    if get_product(code):
        return False
    conn = _conn()
    try:
        nxt = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM products").fetchone()[0]
        conn.execute(
            "INSERT INTO products (code, name, flag, price, max_lzt, filters, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, name, flag, float(price), float(max_lzt), json.dumps(filters or {}), nxt),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error("add_product failed: %s", e)
        return False
    finally:
        conn.close()


def remove_product(code: str) -> bool:
    """Remove a country. Returns True if a row was deleted."""
    conn = _conn()
    try:
        cur = conn.execute("DELETE FROM products WHERE code = ?", (code.upper(),))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error("remove_product failed: %s", e)
        return False
    finally:
        conn.close()


def update_product_price(code: str, price: float) -> bool:
    """Update the INR selling price."""
    conn = _conn()
    try:
        cur = conn.execute(
            "UPDATE products SET price = ? WHERE code = ?", (float(price), code.upper())
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error("update_product_price failed: %s", e)
        return False
    finally:
        conn.close()


def update_product_max_lzt(code: str, max_lzt: float) -> bool:
    """Update the max USD buy cap."""
    conn = _conn()
    try:
        cur = conn.execute(
            "UPDATE products SET max_lzt = ? WHERE code = ?", (float(max_lzt), code.upper())
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error("update_product_max_lzt failed: %s", e)
        return False
    finally:
        conn.close()


def update_product_filters(code: str, filters: dict) -> bool:
    """Update per-country extra filters."""
    conn = _conn()
    try:
        cur = conn.execute(
            "UPDATE products SET filters = ? WHERE code = ?",
            (json.dumps(filters or {}), code.upper()),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error("update_product_filters failed: %s", e)
        return False
    finally:
        conn.close()


def get_effective_filters(product: dict) -> dict:
    """
    EFFECTIVE filters sent to LZT = global defaults + this country's extras.
    Global: nsb=1, spam=no, email=yes. Per-country filters override on top.
    """
    effective = GLOBAL_DEFAULT_FILTERS.copy()
    product_filters = product.get("filters", {})
    if product_filters and isinstance(product_filters, dict):
        effective.update(product_filters)
    return effective
