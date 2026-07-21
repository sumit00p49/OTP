"""
Product Manager - manages countries/products for the shop.
Uses MongoDB for persistent storage (products survive restarts/redeploys).
Fallback to local JSON file if MongoDB is not configured.

DEFAULT FILTERS (auto-applied to ALL countries):
  - nsb=1 (No Spam Block - critical for OTP)
  - telegram_password=0 (No 2FA password)
  - eg=1 (Has Gmail/Email linked)

Admin only needs to add country code, name, flag, price, max_lzt.
Filters are applied AUTOMATICALLY.
"""

import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ==================== DEFAULT FILTERS ====================
# These are ALWAYS applied to every country search.
# Admin doesn't need to set these manually!
GLOBAL_DEFAULT_FILTERS = {
    "nsb": 1,             # No spam block
    "spam": "no",         # No spam block (confirmed from lzt.market URL)
    "email": "yes",       # Has email/Gmail linked (confirmed: email=yes)
    "password": "no",     # No 2FA password — LZT uses yes/no pattern (NOT telegram_password=0)
}

# ==================== MongoDB Backend ====================
_mongo_client = None
_mongo_db = None
_use_mongo = False

PRODUCTS_FILE = "products.json"

# Default products if products.json doesn't exist.
# NOTE: products.json is gitignored — edit it directly on your server.
# This default is only used the very first time (or if the file is deleted).
DEFAULT_PRODUCTS = [
    {"code": "IN", "name": "India", "flag": "\U0001f1ee\U0001f1f3", "price": 26, "max_lzt": 0.12, "filters": {}},
    {"code": "BD", "name": "Bangladesh", "flag": "\U0001f1e7\U0001f1e9", "price": 20, "max_lzt": 0.12, "filters": {}},
    {"code": "ID", "name": "Indonesia", "flag": "\U0001f1ee\U0001f1e9", "price": 25, "max_lzt": 0.12, "filters": {}},
    {"code": "MM", "name": "Myanmar", "flag": "\U0001f1f2\U0001f1f2", "price": 22, "max_lzt": 0.12, "filters": {}},
]


async def init_product_db():
    """Initialize MongoDB connection for products (call once at startup)."""
    global _mongo_client, _mongo_db, _use_mongo

    from config import MONGO_URI
    mongo_uri = MONGO_URI
    if not mongo_uri:
        logger.info("MONGO_URI not set in .env — Using local JSON file for products.")
        _use_mongo = False
        return

    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        _mongo_client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Test connection
        await _mongo_client.admin.command("ping")
        _mongo_db = _mongo_client.get_database("tg_shop_bot")
        _use_mongo = True
        logger.info("MongoDB connected for product storage!")

        # Migrate from JSON to Mongo if needed
        await _migrate_json_to_mongo()
    except ImportError:
        logger.warning("motor not installed. Using JSON file. Install: pip install motor")
        _use_mongo = False
    except Exception as e:
        logger.warning("MongoDB connection failed: %s. Using JSON file.", e)
        _use_mongo = False


async def _migrate_json_to_mongo():
    """If products.json exists and Mongo is empty, migrate data."""
    if not _use_mongo or not _mongo_db:
        return

    collection = _mongo_db["products"]
    count = await collection.count_documents({})
    if count > 0:
        return  # Already has data

    # Load from JSON
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r") as f:
                products = json.load(f)
            if products:
                await collection.insert_many(products)
                logger.info("Migrated %d products from JSON to MongoDB.", len(products))
        except Exception as e:
            logger.error("Migration failed: %s", e)


# ==================== CRUD Operations ====================

def _load_products_json() -> list:
    """Load products from local JSON file (fallback)."""
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to load products.json: %s", e)
    return DEFAULT_PRODUCTS.copy()


def _save_products_json(products: list):
    """Save products to local JSON file."""
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)


async def get_all_products_async() -> list:
    """Get all products (async - MongoDB or JSON)."""
    if _use_mongo and _mongo_db:
        try:
            collection = _mongo_db["products"]
            cursor = collection.find({}, {"_id": 0})
            products = await cursor.to_list(length=100)
            return products if products else DEFAULT_PRODUCTS.copy()
        except Exception as e:
            logger.error("Mongo get_all failed: %s", e)
    return _load_products_json()


def get_all_products() -> list:
    """Get all products (sync - for keyboards that can't await)."""
    # For sync context, always use JSON
    return _load_products_json()


async def get_product_async(code: str) -> Optional[dict]:
    """Get a product by country code (async)."""
    if _use_mongo and _mongo_db:
        try:
            collection = _mongo_db["products"]
            product = await collection.find_one(
                {"code": code.upper()}, {"_id": 0}
            )
            return product
        except Exception as e:
            logger.error("Mongo get_product failed: %s", e)
    return get_product(code)


def get_product(code: str) -> Optional[dict]:
    """Get a product by country code (sync)."""
    for p in _load_products_json():
        if p["code"].upper() == code.upper():
            return p
    return None


async def add_product_async(code: str, name: str, flag: str, price: float, max_lzt: float, extra_filters: dict = None) -> bool:
    """Add a new product (async). Returns False if already exists."""
    product_data = {
        "code": code.upper(),
        "name": name,
        "flag": flag,
        "price": price,
        "max_lzt": max_lzt,
        "filters": extra_filters or {},
    }

    if _use_mongo and _mongo_db:
        try:
            collection = _mongo_db["products"]
            existing = await collection.find_one({"code": code.upper()})
            if existing:
                return False
            await collection.insert_one(product_data)
            # Also save to JSON as backup
            _sync_to_json(product_data, action="add")
            return True
        except Exception as e:
            logger.error("Mongo add_product failed: %s", e)

    # Fallback to JSON
    return add_product(code, name, flag, price, max_lzt, extra_filters or {})


def add_product(code: str, name: str, flag: str, price: float, max_lzt: float, filters: dict) -> bool:
    """Add a new product (sync/JSON). Returns False if already exists."""
    products = _load_products_json()
    for p in products:
        if p["code"].upper() == code.upper():
            return False

    products.append({
        "code": code.upper(),
        "name": name,
        "flag": flag,
        "price": price,
        "max_lzt": max_lzt,
        "filters": filters,
    })
    _save_products_json(products)
    return True


async def remove_product_async(code: str) -> bool:
    """Remove a product (async)."""
    if _use_mongo and _mongo_db:
        try:
            collection = _mongo_db["products"]
            result = await collection.delete_one({"code": code.upper()})
            _sync_to_json({"code": code.upper()}, action="remove")
            return result.deleted_count > 0
        except Exception as e:
            logger.error("Mongo remove failed: %s", e)
    return remove_product(code)


def remove_product(code: str) -> bool:
    """Remove a product (sync/JSON)."""
    products = _load_products_json()
    new_products = [p for p in products if p["code"].upper() != code.upper()]
    if len(new_products) == len(products):
        return False
    _save_products_json(new_products)
    return True


async def update_product_price_async(code: str, price: float) -> bool:
    """Update price (async)."""
    if _use_mongo and _mongo_db:
        try:
            collection = _mongo_db["products"]
            result = await collection.update_one(
                {"code": code.upper()},
                {"$set": {"price": price}}
            )
            # Also update JSON
            update_product_price(code, price)
            return result.modified_count > 0
        except Exception as e:
            logger.error("Mongo update_price failed: %s", e)
    return update_product_price(code, price)


def update_product_price(code: str, price: float) -> bool:
    """Update price (sync/JSON)."""
    products = _load_products_json()
    for p in products:
        if p["code"].upper() == code.upper():
            p["price"] = price
            _save_products_json(products)
            return True
    return False


async def update_product_filters_async(code: str, filters: dict) -> bool:
    """Update filters (async)."""
    if _use_mongo and _mongo_db:
        try:
            collection = _mongo_db["products"]
            result = await collection.update_one(
                {"code": code.upper()},
                {"$set": {"filters": filters}}
            )
            update_product_filters(code, filters)
            return result.modified_count > 0
        except Exception as e:
            logger.error("Mongo update_filters failed: %s", e)
    return update_product_filters(code, filters)


def update_product_filters(code: str, filters: dict) -> bool:
    """Update filters (sync/JSON)."""
    products = _load_products_json()
    for p in products:
        if p["code"].upper() == code.upper():
            p["filters"] = filters
            _save_products_json(products)
            return True
    return False


async def update_product_max_lzt_async(code: str, max_lzt: float) -> bool:
    """Update max LZT price (async)."""
    if _use_mongo and _mongo_db:
        try:
            collection = _mongo_db["products"]
            result = await collection.update_one(
                {"code": code.upper()},
                {"$set": {"max_lzt": max_lzt}}
            )
            update_product_max_lzt(code, max_lzt)
            return result.modified_count > 0
        except Exception as e:
            logger.error("Mongo update_max_lzt failed: %s", e)
    return update_product_max_lzt(code, max_lzt)


def update_product_max_lzt(code: str, max_lzt: float) -> bool:
    """Update max LZT price (sync/JSON)."""
    products = _load_products_json()
    for p in products:
        if p["code"].upper() == code.upper():
            p["max_lzt"] = max_lzt
            _save_products_json(products)
            return True
    return False


def get_effective_filters(product: dict) -> dict:
    """
    Get the EFFECTIVE filters for a product = GLOBAL defaults + product-specific overrides.
    
    This is what actually gets sent to the LZT API.
    Global defaults: nsb=1, telegram_password=0, eg=1
    Product can ADD extra filters (like origin[]) but cannot disable globals unless explicitly overridden.
    """
    # Start with global defaults
    effective = GLOBAL_DEFAULT_FILTERS.copy()
    
    # Merge product-specific filters (overrides globals if same key)
    product_filters = product.get("filters", {})
    if product_filters:
        effective.update(product_filters)
    
    return effective


def _sync_to_json(product_data: dict, action: str):
    """Keep JSON file in sync with MongoDB (backup)."""
    try:
        products = _load_products_json()
        if action == "add":
            # Remove _id if present
            clean = {k: v for k, v in product_data.items() if k != "_id"}
            products.append(clean)
        elif action == "remove":
            products = [p for p in products if p["code"].upper() != product_data["code"].upper()]
        _save_products_json(products)
    except Exception:
        pass


# Initialize JSON file if not exists
if not os.path.exists(PRODUCTS_FILE):
    _save_products_json(DEFAULT_PRODUCTS)
