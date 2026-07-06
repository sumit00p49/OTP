"""
LZT Market API client.
Handles searching and purchasing Telegram accounts.
"""

import aiohttp
import json
from typing import Optional
from config import LZT_API_KEY, LZT_BASE_URL, LZT_CATEGORY


class LZTAPIError(Exception):
    """Custom exception for LZT API errors."""

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
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=self._headers(),
            )
        return self._session

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> dict:
        """Make an API request."""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with session.request(method, url, params=params, json=data) as response:
                try:
                    result = await response.json()
                except (aiohttp.ContentTypeError, ValueError):
                    text = await response.text()
                    raise LZTAPIError(f"Invalid API response: {text[:200]}", response.status)

                if response.status != 200:
                    error_msg = result.get("error", result.get("message", f"HTTP {response.status}"))
                    raise LZTAPIError(str(error_msg), response.status)

                return result

        except aiohttp.ClientConnectorError:
            raise LZTAPIError("Cannot connect to LZT Market API.")
        except aiohttp.ClientError as e:
            raise LZTAPIError(f"Network error: {str(e)}")

    async def search_accounts(
        self,
        country: str = None,
        quality: str = "cheap",
        limit: int = 1,
    ) -> dict:
        """
        Search for available Telegram accounts.

        Args:
            country: Country code (e.g., 'IN', 'US') or None for random
            quality: 'cheap' or 'good'
            limit: Number of results

        Returns:
            API response with available accounts
        """
        params = {
            "category_id": LZT_CATEGORY,
            "order_by": "price_to_up" if quality == "cheap" else "pdate_to_down",
        }

        if quality == "good":
            params["origin[]"] = ["autoreg", "personal"]

        if country and country.lower() != "random":
            params["country[]"] = country

        params["limit"] = limit

        return await self._request("GET", f"/{LZT_CATEGORY}/", params=params)

    async def buy_account(self, item_id: int) -> dict:
        """
        Purchase an account by item ID.

        Args:
            item_id: The LZT item ID to purchase

        Returns:
            API response with account details
        """
        return await self._request("POST", f"/{item_id}/fast-buy")

    async def get_account_details(self, item_id: int) -> dict:
        """
        Get purchased account details.

        Args:
            item_id: The purchased item ID

        Returns:
            Account details (phone, password, 2FA, etc.)
        """
        return await self._request("GET", f"/{item_id}/")

    async def check_stock(self, country: str = None, quality: str = "cheap") -> bool:
        """Check if accounts are available for given criteria."""
        try:
            result = await self.search_accounts(country=country, quality=quality, limit=1)
            items = result.get("items", [])
            return len(items) > 0
        except LZTAPIError:
            return False


# Singleton instance
lzt_api = LZTMarketAPI()
