"""
LZT Market API client (https://prod-api.lzt.market).

Endpoints used:
- GET  /me                             → seller profile + balance
- GET  /telegram?country[]=IN&order_by=price_to_up → search India accounts
- POST /{item_id}/fast-buy             → atomic purchase (with price guard)
- GET  /{item_id}/telegram-login-code  → fetch live OTP
- GET  /{item_id}                      → full item/login data
"""

import asyncio
import logging
import aiohttp
from typing import Optional

from config import LZT_API_KEY, LZT_BASE_URL

logger = logging.getLogger(__name__)


class LZTAPIError(Exception):
    """Raised when the LZT API returns an error."""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class LZTMarketAPI:
    """Async client for LZT Market API."""

    def __init__(self):
        self.base_url = LZT_BASE_URL.rstrip("/")
        self.api_key = LZT_API_KEY
        self._session: Optional[aiohttp.ClientSession] = None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=40),
                headers=self._headers(),
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, endpoint: str, params=None, data=None, retries=2) -> dict:
        """Make API request with rate-limit retry."""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with session.request(method, url, params=params, json=data) as resp:
                # Rate limited — wait and retry
                if resp.status == 429 and retries > 0:
                    wait = int(resp.headers.get("Retry-After", "3"))
                    logger.warning("Rate limited. Waiting %ss...", wait)
                    await asyncio.sleep(wait)
                    return await self._request(method, endpoint, params, data, retries - 1)

                try:
                    result = await resp.json()
                except Exception:
                    text = await resp.text()
                    raise LZTAPIError(f"Non-JSON response: {text[:200]}", resp.status)

                if resp.status >= 400:
                    msg = self._extract_error(result, resp.status)
                    raise LZTAPIError(msg, resp.status)

                # Log raw on first success (helps debugging)
                logger.debug("LZT %s %s -> %s", method, endpoint, str(result)[:300])
                return result

        except aiohttp.ClientConnectorError:
            raise LZTAPIError("Cannot connect to LZT Market.")
        except asyncio.TimeoutError:
            raise LZTAPIError("LZT API timed out.")
        except aiohttp.ClientError as e:
            raise LZTAPIError(f"Network error: {e}")

    @staticmethod
    def _extract_error(result: dict, status: int) -> str:
        if isinstance(result, dict):
            if result.get("errors"):
                errs = result["errors"]
                return str(errs[0]) if isinstance(errs, list) and errs else str(errs)
            for k in ("error", "message", "error_description"):
                if result.get(k):
                    return str(result[k])
        return f"HTTP {status}"

    # ==================== Endpoints ====================

    async def get_me(self) -> dict:
        """GET /me — seller profile + balance."""
        return await self._request("GET", "/me")

    async def get_seller_balance(self) -> Optional[float]:
        """Return seller balance or None on error."""
        try:
            data = await self.get_me()
            user = data.get("user", data)
            return float(user.get("balance", 0))
        except Exception:
            return None

    async def search_accounts(self, country: str = "IN", pmax: float = None, extra_filters: dict = None) -> list:
        """
        Search Telegram accounts with per-country filters.
        
        IMPORTANT: All filter values must be sent as proper types to aiohttp.
        LZT API filter keys:
          - nsb=1          → No spam block (CRITICAL for OTP accounts!)
          - sb=1           → Has spam block
          - telegram_password=0 → No 2FA password
          - telegram_password=1 → Has 2FA password
          - origin[]=resale/autoreg/personal/stealer
          - not_sold_before=1 → Never sold
          - telegram_premium=1 → Has premium
        """
        # Fix common country code mistakes
        country = _fix_country_code(country)

        params = {
            "country[]": country,
            "order_by": "price_to_up",
        }
        if pmax is not None:
            params["pmax"] = str(pmax)

        # Apply per-country filters from PRODUCTS config
        # CRITICAL: Each filter must be included as a query parameter
        if extra_filters and isinstance(extra_filters, dict):
            for key, value in extra_filters.items():
                # Convert all values to string for consistent HTTP params
                params[key] = str(value) if value is not None else ""

        logger.info("LZT search params: %s", params)
        result = await self._request("GET", "/telegram", params=params)
        items = result.get("items", [])
        if isinstance(items, dict):
            items = list(items.values())
        return items if isinstance(items, list) else []

    async def get_stock_count(self, country: str = "IN", pmax: float = None, extra_filters: dict = None) -> int:
        """Get total available stock count for a country (with pmax + filters)."""
        country = _fix_country_code(country)
        params = {
            "country[]": country,
            "order_by": "price_to_up",
        }
        if pmax is not None:
            params["pmax"] = str(pmax)
        if extra_filters and isinstance(extra_filters, dict):
            for key, value in extra_filters.items():
                params[key] = str(value) if value is not None else ""

        try:
            result = await self._request("GET", "/telegram", params=params)
            total = result.get("totalItems", result.get("total_items", 0))
            if not total:
                items = result.get("items", [])
                if isinstance(items, dict):
                    total = len(items)
                elif isinstance(items, list):
                    total = len(items)
            return int(total)
        except Exception:
            return 0

    async def buy(self, item_id, price: float = None, currency: str = None) -> dict:
        """POST /{item_id}/fast-buy — atomic purchase with optional price guard."""
        data = {}
        if price is not None:
            data["price"] = price
        if currency:
            data["currency"] = currency
        return await self._request("POST", f"/{item_id}/fast-buy", data=data or None)

    async def get_item(self, item_id) -> dict:
        """GET /{item_id} — full item details (login data after purchase)."""
        return await self._request("GET", f"/{item_id}")

    async def get_telegram_login_code(self, item_id) -> Optional[str]:
        """
        Request Telegram login code for a purchased account.
        
        CONFIRMED from real API test:
        - Method: GET (POST returns 404)
        - Endpoint: GET /{item_id}/telegram-login-code
        - Response: {"item": {...}, "codes": [{"code": "12345", ...}]}
        - Code is in: result["codes"][0]["code"]
        
        NOTE: Only works if item has showGetTelegramCodeButton: True
        (accounts with spamblock may have this disabled)
        """
        try:
            result = await self._request("GET", f"/{item_id}/telegram-login-code")
            logger.info("telegram-login-code for %s: keys=%s", item_id, list(result.keys()))

            # PRIMARY: codes array (confirmed from real response)
            codes = result.get("codes", [])
            if codes and isinstance(codes, list) and len(codes) > 0:
                first_code = codes[0]
                if isinstance(first_code, dict):
                    code = first_code.get("code") or first_code.get("login_code")
                elif isinstance(first_code, str):
                    code = first_code
                else:
                    code = str(first_code)
                if code:
                    return str(code)

            # FALLBACK: direct fields
            code = (
                result.get("code")
                or result.get("login_code")
                or result.get("loginCode")
            )
            if code:
                return str(code)

            # Item nested
            item = result.get("item", {})
            if isinstance(item, dict):
                code = item.get("code") or item.get("login_code")
                if code:
                    return str(code)

            logger.info("No code found in response for %s", item_id)
            return None

        except LZTAPIError as e:
            logger.warning("telegram-login-code failed for %s: %s", item_id, e.message)
            return None

    @staticmethod
    def extract_account_data(payload: dict) -> dict:
        """
        Normalize account details from a buy/item response.

        REAL LZT BEHAVIOR (confirmed from test_api.py output):
        - Search results: phone/loginData are EMPTY (canViewLoginData: false)
        - After purchase: GET /{item_id} returns loginData with auth key
        - Phone is in a separate field that only appears after ownership
        
        Known fields after purchase:
        - item.telegramPhone or item.telegram_phone_number
        - loginData.login = auth key (HEX), NOT phone
        - loginData.password = 2FA password (if exists)
        - item.accountLink = phone number sometimes
        """
        item = payload.get("item", payload)
        login_data = item.get("loginData", {}) or {}

        # Phone number (CONFIRMED: telegram_phone field)
        phone = (
            item.get("telegram_formatted_phone")  # "+91 93420 65997" (nice format)
            or item.get("telegram_phone")          # "919342065997"
            or ""
        )

        # If still no phone, check login field (only if it looks like a phone)
        if not phone:
            login_field = item.get("login") or ""
            clean = login_field.replace("+", "").replace(" ", "")
            if clean.isdigit() and len(clean) <= 15:
                phone = login_field

        if not phone:
            phone = _extract_phone_from_title(item.get("title", ""))

        if not phone:
            phone = "N/A"

        # Auth key (the big hex string in "login" field)
        auth_key = ""
        login_field = item.get("login") or ""
        if len(login_field) > 30:
            auth_key = login_field

        # 2FA Password (CONFIRMED: loginData["password"])
        password = login_data.get("password") or login_data.get("encodedPassword") or ""

        # Username
        username = item.get("telegram_username") or ""

        # Whether OTP is available for this account
        otp_available = item.get("showGetTelegramCodeButton", False)

        return {
            "item_id": str(item.get("item_id", item.get("id", ""))),
            "phone": phone,
            "auth_key": auth_key,
            "password": password,
            "2fa": password,  # For telegram category, password IS the 2FA code
            "username": username,
            "otp_available": otp_available,
            "has_tdata": bool(item.get("telegram_json")),
        }


def _extract_phone_from_title(title: str) -> str:
    """
    Try to extract a phone number from the item title.
    LZT titles look like: "+880 +91 +62 | Second hand account |"
    We want the actual phone, which is usually in a more specific field.
    If title starts with digits or +, extract it.
    """
    if not title:
        return ""
    # If title contains a clear phone pattern
    import re
    # Match patterns like "916239430752" or "+91 6239430752" or "+916239430752"
    match = re.search(r'(\+?\d[\d\s]{8,15})', title)
    if match:
        phone = match.group(1).replace(" ", "")
        # Only return if it's a reasonable phone number length (not an auth key)
        if 8 <= len(phone.replace("+", "")) <= 15:
            return phone
    return ""


def _fix_country_code(code: str) -> str:
    """Fix common country code mistakes. LZT uses ISO 3166-1 alpha-2."""
    fixes = {
        "UK": "GB",   # United Kingdom = GB (not UK!)
        "EN": "GB",   # England = GB
        "KO": "KR",   # Korea = KR
        "JP": "JP",   # Japan (correct)
    }
    upper = code.upper().strip()
    return fixes.get(upper, upper)


# Singleton
lzt_api = LZTMarketAPI()
