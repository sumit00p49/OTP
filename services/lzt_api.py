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

    async def search_accounts(self, country: str = "IN", pmax: float = None) -> list:
        """
        Search cheapest India Telegram accounts.
        Returns list of item dicts (may be empty).
        """
        params = {
            "country[]": country,
            "order_by": "price_to_up",
        }
        if pmax is not None:
            params["pmax"] = pmax

        result = await self._request("GET", "/telegram", params=params)
        items = result.get("items", [])
        # items can be dict (keyed by id) or list
        if isinstance(items, dict):
            items = list(items.values())
        return items if isinstance(items, list) else []

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
        Request a fresh Telegram login code for a purchased account.
        
        LZT Web UI button: "Get a code" 
        Tries both POST and GET methods (LZT docs are unclear on which).
        The endpoint REQUESTS a code to be sent to the account, then returns it.
        """
        # Try POST first (LZT web UI uses POST for "Get a code" button)
        try:
            result = await self._request("POST", f"/{item_id}/telegram-login-code")
            logger.info("telegram-login-code POST for %s: %s", item_id, str(result)[:500])
            code = self._extract_code_from_response(result)
            if code:
                return code
        except LZTAPIError as e:
            logger.info("POST telegram-login-code failed for %s: %s — trying GET", item_id, e.message)

        # Fallback: try GET
        try:
            result = await self._request("GET", f"/{item_id}/telegram-login-code")
            logger.info("telegram-login-code GET for %s: %s", item_id, str(result)[:500])
            code = self._extract_code_from_response(result)
            if code:
                return code
        except LZTAPIError as e:
            logger.warning("GET telegram-login-code also failed for %s: %s", item_id, e.message)

        # Try alternative endpoint path
        try:
            result = await self._request("POST", f"/{item_id}/request-code")
            logger.info("request-code for %s: %s", item_id, str(result)[:500])
            code = self._extract_code_from_response(result)
            if code:
                return code
        except LZTAPIError:
            pass

        return None

    @staticmethod
    def _extract_code_from_response(result: dict) -> Optional[str]:
        """Extract OTP code from various response formats."""
        if not result or not isinstance(result, dict):
            return None

        # Direct fields
        code = (
            result.get("code")
            or result.get("login_code")
            or result.get("loginCode")
            or result.get("telegramCode")
            or result.get("telegram_code")
        )
        if code:
            return str(code)

        # Nested in "item"
        item = result.get("item", {})
        if isinstance(item, dict):
            code = (
                item.get("code")
                or item.get("login_code")
                or item.get("loginCode")
                or item.get("telegramCode")
                or item.get("telegram_code")
            )
            if code:
                return str(code)

            # Inside loginData
            login_data = item.get("loginData", {}) or {}
            code = login_data.get("code") or login_data.get("login_code")
            if code:
                return str(code)

        # Sometimes just "message" contains the code as text
        msg = result.get("message", "")
        if msg and msg.isdigit() and 4 <= len(msg) <= 8:
            return msg

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

        # Phone number extraction — check ALL possible fields
        # Priority: dedicated phone fields > accountLink > title parsing
        phone = (
            item.get("telegramPhone")
            or item.get("telegram_phone_number")
            or item.get("telegram_phone")
            or item.get("account_phone")
            or item.get("phone")
            or item.get("phoneNumber")
            or ""
        )

        # Check accountLink / accountLinks (sometimes has the phone)
        if not phone:
            account_link = item.get("accountLink") or ""
            if account_link and any(c.isdigit() for c in account_link):
                phone = account_link

        # Check loginData for phone (some responses put it differently)
        if not phone:
            phone = login_data.get("phone") or login_data.get("phoneNumber") or ""

        # loginData.login is the AUTH KEY (hex) — check if it's actually a phone
        # Phone numbers are max 15 digits, auth keys are 64+ hex chars
        login_field = login_data.get("login") or ""
        if not phone and login_field:
            # Only use it if it looks like a phone (short, numeric)
            clean = login_field.replace("+", "").replace(" ", "")
            if clean.isdigit() and len(clean) <= 15:
                phone = login_field

        # If still no phone, try title parsing
        if not phone:
            phone = _extract_phone_from_title(item.get("title", ""))

        if not phone:
            phone = "N/A"

        # Auth key
        auth_key = ""
        if login_field and len(login_field) > 20:
            auth_key = login_field

        # Password / 2FA
        password = login_data.get("password") or item.get("account_password") or ""
        twofa = login_data.get("2fa") or login_data.get("twofa") or item.get("account_2fa") or ""

        return {
            "item_id": str(item.get("item_id", item.get("id", ""))),
            "phone": phone,
            "auth_key": auth_key,
            "password": password,
            "2fa": twofa,
            "has_tdata": bool(item.get("telegram_json") or item.get("hasTdata")),
            "raw_login": login_data,
            "raw_keys": list(item.keys())[:20],  # Debug: first 20 keys
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


# Singleton
lzt_api = LZTMarketAPI()
