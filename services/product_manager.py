"""
Product Manager - manages countries/products for the shop.
Stores in products.json file so admin can add/remove/edit via bot.
No .env editing needed!
"""

import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

PRODUCTS_FILE = "products.json"

# Default product if file doesn't exist
DEFAULT_PRODUCTS = [
    {
        "code": "IN",
        "name": "India",
        "flag": "🇮🇳",
        "price": 70,
        "max_lzt": 0.15,
        "filters": {
            "origin[]": "resale",
            "telegram_password": 0,
            "nsb": 1,  # No spam block = OTP works!
        }
    }
]


def _load_products() -> list:
    """Load products from JSON file."""
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to load products.json: %s", e)
    return DEFAULT_PRODUCTS.copy()


def _save_products(products: list):
    """Save products to JSON file."""
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)


def get_all_products() -> list:
    """Get all products."""
    return _load_products()


def get_product(code: str) -> Optional[dict]:
    """Get a product by country code."""
    for p in _load_products():
        if p["code"].upper() == code.upper():
            return p
    return None


def add_product(code: str, name: str, flag: str, price: float, max_lzt: float, filters: dict) -> bool:
    """Add a new product. Returns False if already exists."""
    products = _load_products()

    # Check if already exists
    for p in products:
        if p["code"].upper() == code.upper():
            return False

    # Always add nsb=1 for OTP support
    if "nsb" not in filters:
        filters["nsb"] = 1

    products.append({
        "code": code.upper(),
        "name": name,
        "flag": flag,
        "price": price,
        "max_lzt": max_lzt,
        "filters": filters,
    })
    _save_products(products)
    return True


def remove_product(code: str) -> bool:
    """Remove a product by country code. Returns False if not found."""
    products = _load_products()
    new_products = [p for p in products if p["code"].upper() != code.upper()]
    if len(new_products) == len(products):
        return False
    _save_products(new_products)
    return True


def update_product_price(code: str, price: float) -> bool:
    """Update price for a product."""
    products = _load_products()
    for p in products:
        if p["code"].upper() == code.upper():
            p["price"] = price
            _save_products(products)
            return True
    return False


def update_product_filters(code: str, filters: dict) -> bool:
    """Update filters for a product."""
    products = _load_products()
    for p in products:
        if p["code"].upper() == code.upper():
            # Always keep nsb=1 for OTP
            if "nsb" not in filters:
                filters["nsb"] = 1
            p["filters"] = filters
            _save_products(products)
            return True
    return False


# Initialize products file if not exists
if not os.path.exists(PRODUCTS_FILE):
    _save_products(DEFAULT_PRODUCTS)
