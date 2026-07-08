"""
🔧 API DIAGNOSTIC TOOL
======================
Run this ONCE on your PC/server to see EXACTLY what your store API returns.
It does NOT touch the bot. It just prints the raw responses so we can fix the
account-fetch logic to match your store's real format.

HOW TO RUN:
    1. Make sure your .env has LZT_API_KEY and LZT_BASE_URL filled in.
    2. pip install aiohttp python-dotenv
    3. python test_api.py
    4. Copy ALL the output and send it back to me.

⚠️ The output may contain your balance/stock info but NOT your full API key
   (we mask it). Safe to share with me.
"""

import asyncio
import json
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LZT_API_KEY", "")
BASE_URL = os.getenv("LZT_BASE_URL", "https://prod-api.lzt.market").rstrip("/")
CATEGORY = os.getenv("LZT_CATEGORY", "telegram")


def mask(key: str) -> str:
    if not key or len(key) < 8:
        return "(empty or too short!)"
    return f"{key[:4]}...{key[-4:]} (length={len(key)})"


def show(title: str, status, data):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print(f"HTTP status: {status}")
    try:
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2500])
    except Exception:
        print(str(data)[:2500])


async def hit(session, method, path, params=None):
    url = f"{BASE_URL}/{path.lstrip('/')}"
    try:
        async with session.request(method, url, params=params) as r:
            try:
                data = await r.json()
            except Exception:
                data = await r.text()
            return r.status, data
    except Exception as e:
        return "ERROR", f"{type(e).__name__}: {e}"


async def main():
    print("\n🔧 STORE API DIAGNOSTIC")
    print(f"Base URL : {BASE_URL}")
    print(f"Category : {CATEGORY}")
    print(f"API Key  : {mask(API_KEY)}")

    if not API_KEY or API_KEY == "YOUR_LZT_API_KEY_HERE":
        print("\n❌ LZT_API_KEY is not set in .env! Fill it in first.")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession(
        headers=headers, timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        # 1) Balance / profile
        status, data = await hit(session, "GET", "/me")
        show("TEST 1: Balance check  ->  GET /me", status, data)

        # 2) Search stock in the category
        status, data = await hit(
            session, "GET", f"/{CATEGORY}", params={"country[]": "IN", "order_by": "price_to_up"}
        )
        show(f"TEST 2: India stock  ->  GET /{CATEGORY}?country[]=IN", status, data)

        # If we found items, show the first item's fields
        if isinstance(data, dict) and data.get("items"):
            items = data["items"]
            if isinstance(items, dict):
                first_item = list(items.values())[0]
            elif isinstance(items, list) and items:
                first_item = items[0]
            else:
                first_item = None

            if first_item:
                show("TEST 2b: First item details (FIELD NAMES)", "—", {
                    "item_id": first_item.get("item_id"),
                    "title": first_item.get("title"),
                    "price": first_item.get("price"),
                    "telegramPhone": first_item.get("telegramPhone"),
                    "telegram_phone": first_item.get("telegram_phone"),
                    "account_phone": first_item.get("account_phone"),
                    "phone": first_item.get("phone"),
                    "loginData_keys": list((first_item.get("loginData") or {}).keys()),
                    "ALL_KEYS": list(first_item.keys()),
                })

        # 3) Category list
        status, data = await hit(session, "GET", "/category")
        show("TEST 3: Categories  ->  GET /category", status, data)

    print("\n" + "=" * 60)
    print("  ✅ DONE. Copy everything above and send it to me.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
