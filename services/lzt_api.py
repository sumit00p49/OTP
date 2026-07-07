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
        """Fetch latest Telegram login code for a purchased account."""
        try:
            result = await self._request("GET", f"/{item_id}/telegram-login-code")
            return result.get("code") or result.get("login_code")
        except LZTAPIError:
            return None

    @staticmethod
    def extract_account_data(payload: dict) -> dict:
        """Normalize account details from a buy/item response."""
        item = payload.get("item", payload)
        login_data = item.get("loginData", {}) or {}

        phone = (
            login_data.get("login")
            or item.get("account_phone")
            or item.get("telegram_phone")
            or item.get("title", "N/A")
        )
        password = login_data.get("password") or item.get("account_password") or ""
        twofa = login_data.get("2fa") or item.get("account_2fa") or ""

        return {
            "item_id": str(item.get("item_id", item.get("id", ""))),
            "phone": phone,
            "password": password or "N/A",
            "2fa": twofa,
            "has_tdata": bool(item.get("telegram_json") or item.get("hasTdata")),
            "raw_login": login_data,
        }


# Singleton
lzt_api = LZTMarketAPI()
