"""
🔧 OTP ENDPOINT TESTER
======================
Tests the "Get a code" (telegram-login-code) endpoint for a specific item.

USAGE:
    python test_otp.py <item_id>
    
    Example: python test_otp.py 245265723
    
    (Use an item_id of an account you already BOUGHT)
"""

import asyncio
import json
import sys
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LZT_API_KEY", "")
BASE_URL = os.getenv("LZT_BASE_URL", "https://prod-api.lzt.market").rstrip("/")


def show(title, status, data):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print(f"Status: {status}")
    try:
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
    except Exception:
        print(str(data)[:3000])


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_otp.py <item_id>")
        print("Use the item_id of an account you already BOUGHT")
        return

    item_id = sys.argv[1]
    print(f"\n🔧 Testing OTP for item: {item_id}")
    print(f"Base URL: {BASE_URL}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession(
        headers=headers, timeout=aiohttp.ClientTimeout(total=30)
    ) as session:

        # 1) First get the item details (to see if phone is there)
        url = f"{BASE_URL}/{item_id}"
        async with session.get(url) as r:
            data = await r.json() if r.status == 200 else await r.text()
            show(f"TEST 1: GET /{item_id} (item details after purchase)", r.status, data)

            # Show phone-related fields specifically
            if isinstance(data, dict):
                item = data.get("item", data)
                print("\n📱 PHONE-RELATED FIELDS:")
                for key in sorted(item.keys()):
                    if any(x in key.lower() for x in ["phone", "login", "telegram"]):
                        print(f"  {key}: {item[key]}")

        # 2) Try POST /telegram-login-code
        url = f"{BASE_URL}/{item_id}/telegram-login-code"
        async with session.post(url) as r:
            try:
                data = await r.json()
            except Exception:
                data = await r.text()
            show(f"TEST 2: POST /{item_id}/telegram-login-code", r.status, data)

        # 3) Try GET /telegram-login-code
        async with session.get(url) as r:
            try:
                data = await r.json()
            except Exception:
                data = await r.text()
            show(f"TEST 3: GET /{item_id}/telegram-login-code", r.status, data)

        # 4) Try alternative paths
        for path in [f"/{item_id}/request-code", f"/{item_id}/get-code"]:
            url = f"{BASE_URL}{path}"
            async with session.post(url) as r:
                try:
                    data = await r.json()
                except Exception:
                    data = await r.text()
                show(f"TEST 4: POST {path}", r.status, data)

    print("\n" + "=" * 60)
    print("  ✅ DONE. Copy ALL output above and send to me.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
