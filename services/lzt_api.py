"""
LZT Market API client (https://prod-api.lzt.market).

Verified against the official docs at https://lzt-market.readme.io :
- Auth via `Authorization: Bearer <token>`
- Balance/profile:      GET  /me
- Search a category:    GET  /{category}
- Fast buy (atomic):    POST /{item_id}/fast-buy
- Reserve then confirm: POST /{item_id}/reserve, POST /{item_id}/confirm-buy
- Cancel reservation:   POST /{item_id}/cancel-reserve
- Validate account:     POST /{item_id}/check
- Item / login data:    GET  /{item_id}
- Telegram login code:  GET  /{item_id}/telegram-login-code
"""

import asyncio
import logging
import aiohttp
from typing import Optional

from config import LZT_API_KEY, LZT_BASE_URL, LZT_CATEGORY

logger = logging.getLogger(__name__)


class LZTAPIError(Exception):
    """Raised when the LZT API returns an error or is unreachable."""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)



class LZTMarketAPI:
    """Async client for the LZT Market API."""

    def __init__(self):
        self.base_url = LZT_BASE_URL.rstrip("/")
        self.api_key = LZT_API_KEY
        self._session: Optional[aiohttp.ClientSession] = None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
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

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        data: dict = None,
        _retries: int = 2,
    ) -> dict:
        """Make an API request with rate-limit retry and error handling."""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with session.request(method, url, params=params, json=data) as response:
                # Rate limited -> back off and retry
                if response.status == 429 and _retries > 0:
                    retry_after = int(response.headers.get("Retry-After", "2"))
                    logger.warning("LZT rate limited. Retrying in %ss", retry_after)
                    await asyncio.sleep(retry_after)
                    return await self._request(method, endpoint, params, data, _retries - 1)

                try:
                    result = await response.json()
                except (aiohttp.ContentTypeError, ValueError):
                    text = await response.text()
                    raise LZTAPIError(f"Invalid API response: {text[:200]}", response.status)

                if response.status >= 400:
                    error_msg = self._extract_error(result, response.status)
                    raise LZTAPIError(error_msg, response.status)

                return result

        except aiohttp.ClientConnectorError:
            raise LZTAPIError("Cannot connect to LZT Market API.")
        except asyncio.TimeoutError:
            raise LZTAPIError("LZT Market API timed out. Try again.")
        except aiohttp.ClientError as e:
            raise LZTAPIError(f"Network error: {str(e)}")

    @staticmethod
    def _extract_error(result: dict, status: int) -> str:
        """Pull a human-readable error message out of an LZT error body."""
        if isinstance(result, dict):
            # LZT returns errors in different shapes across endpoints
            if result.get("errors"):
                errs = result["errors"]
                if isinstance(errs, list) and errs:
                    return str(errs[0])
                return str(errs)
            for key in ("error", "message", "error_description"):
                if result.get(key):
                    return str(result[key])
        return f"HTTP {status}"



    # ==================== Profile / Balance ====================

    async def get_me(self) -> dict:
        """GET /me — returns the authenticated user's profile and balance."""
        return await self._request("GET", "/me")

    async def get_seller_balance(self) -> Optional[float]:
        """Return the seller account balance (best-effort), or None."""
        try:
            data = await self.get_me()
            user = data.get("user", data)
            balance = user.get("balance")
            return float(balance) if balance is not None else None
        except (LZTAPIError, ValueError, TypeError):
            return None

    # ==================== Search ====================

    async def search_accounts(
        self,
        country: str = None,
        quality: str = "cheap",
        limit: int = 1,
        pmax: float = None,
    ) -> list:
        """
        Search available Telegram accounts.

        Args:
            country: 2-letter country code, or None/"RANDOM" for any
            quality: 'cheap' (all origins, cheapest first) or 'good'
                     (autoreg/personal only, freshest first)
            limit: max results to consider
            pmax: max price filter (in the category's currency)

        Returns:
            List of item dicts (may be empty).
        """
        params = {
            "order_by": "price_to_up" if quality == "cheap" else "pdate_to_down",
            "page": 1,
        }

        if quality == "good":
            # Higher-trust origins only
            params["origin[]"] = ["autoreg", "personal"]

        if country and str(country).upper() != "RANDOM":
            params["country[]"] = str(country).upper()

        if pmax is not None:
            params["pmax"] = pmax

        result = await self._request("GET", f"/{LZT_CATEGORY}", params=params)
        items = result.get("items", [])
        if isinstance(items, dict):
            items = list(items.values())
        return items[:limit] if isinstance(items, list) else []



    # ==================== Buying ====================

    async def fast_buy(self, item_id: int, price: float = None, currency: str = None) -> dict:
        """
        Atomic purchase. Passing `price` protects against price changes:
        the API rejects the buy if the current price differs.
        """
        data = {}
        if price is not None:
            data["price"] = price
        if currency:
            data["currency"] = currency
        return await self._request("POST", f"/{item_id}/fast-buy", data=data or None)

    async def reserve(self, item_id: int, price: float = None) -> dict:
        """Reserve an item before confirming (step 1 of safe buy)."""
        data = {"price": price} if price is not None else None
        return await self._request("POST", f"/{item_id}/reserve", data=data)

    async def confirm_buy(self, item_id: int) -> dict:
        """Confirm a reserved purchase (step 2 of safe buy)."""
        return await self._request("POST", f"/{item_id}/confirm-buy")

    async def cancel_reserve(self, item_id: int) -> dict:
        """Cancel a reservation."""
        return await self._request("POST", f"/{item_id}/cancel-reserve")

    async def check_account(self, item_id: int) -> dict:
        """Validate an account before buying."""
        return await self._request("POST", f"/{item_id}/check")

    # ==================== Account Data ====================

    async def get_item(self, item_id: int) -> dict:
        """GET /{item_id} — full item incl. login data after purchase."""
        return await self._request("GET", f"/{item_id}")

    async def get_telegram_login_code(self, item_id: int) -> Optional[str]:
        """Fetch the latest Telegram login code for a purchased account."""
        try:
            result = await self._request("GET", f"/{item_id}/telegram-login-code")
            return result.get("code") or result.get("login_code")
        except LZTAPIError:
            return None



    # ==================== High-level Helpers ====================

    @staticmethod
    def extract_price(item: dict) -> tuple[float, str]:
        """
        Pull (price, currency) from a search item, defensively.
        LZT items expose `price` and `price_currency` (e.g. 'usd', 'rub').
        """
        price = item.get("price", item.get("priceWithSellerFee", 0)) or 0
        currency = (
            item.get("price_currency")
            or item.get("currency")
            or "usd"
        )
        try:
            return float(price), str(currency).lower()
        except (ValueError, TypeError):
            return 0.0, "usd"

    @staticmethod
    def extract_account_data(payload: dict) -> dict:
        """
        Normalize account/login details from a buy or item response.
        Telegram accounts deliver a phone/login, optional password/2FA,
        and TData (session) which the buyer downloads from LZT.
        """
        # The item may be nested under "item"
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

    async def buy(self, item_id: int, price: float = None, currency: str = None) -> dict:
        """
        Purchase dispatch based on BUY_METHOD config.
        - 'reserve': reserve -> confirm-buy (safer, validates first)
        - anything else: fast-buy (atomic)
        Returns the buy response payload.
        """
        from config import BUY_METHOD

        if BUY_METHOD == "reserve":
            await self.reserve(item_id, price=price)
            try:
                return await self.confirm_buy(item_id)
            except LZTAPIError:
                # Best-effort rollback of the reservation
                await self.cancel_reserve(item_id)
                raise
        return await self.fast_buy(item_id, price=price, currency=currency)


# Singleton instance
lzt_api = LZTMarketAPI()
