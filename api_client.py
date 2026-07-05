"""
Async API client for OTPNOW API.
Handles all HTTP requests to the OTP service with proper error handling.
"""

import asyncio
import aiohttp
from typing import Optional
from config import API_BASE_URL, API_KEY


class APIError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class OTPNowAPI:
    """Async client for the OTPNOW API."""

    def __init__(self):
        self.base_url = API_BASE_URL.rstrip("/")
        self.api_key = API_KEY
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """
        Make an API request with error handling.

        Args:
            method: HTTP method (GET or POST)
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            APIError: If the request fails or API returns an error
        """
        session = await self._get_session()

        # Always include api_key in params
        if params is None:
            params = {}
        params["api_key"] = self.api_key

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with session.request(method, url, params=params) as response:
                # Try to parse JSON response
                try:
                    data = await response.json()
                except (aiohttp.ContentTypeError, ValueError):
                    text = await response.text()
                    raise APIError(
                        f"Invalid response from API: {text[:200]}",
                        status_code=response.status,
                    )

                # Check for HTTP errors
                if response.status != 200:
                    error_msg = data.get("message", data.get("error", f"HTTP {response.status}"))
                    raise APIError(error_msg, status_code=response.status)

                # Check for API-level errors in response
                if isinstance(data, dict):
                    if data.get("status") == "error" or data.get("success") is False:
                        error_msg = data.get("message", data.get("error", "Unknown API error"))
                        raise APIError(error_msg)

                return data

        except aiohttp.ClientConnectorError:
            raise APIError("Could not connect to the API server. Please try again later.")
        except aiohttp.ClientError as e:
            raise APIError(f"Network error: {str(e)}")
        except asyncio.TimeoutError:
            raise APIError("Request timed out. Please try again later.")

    # ==================== Balance / Check ====================

    async def check_balance(self) -> dict:
        """
        Check account balance.

        Returns:
            dict with balance information
        """
        return await self._request("GET", "/check")

    # ==================== Telegram Services ====================

    async def tg_countries(self) -> dict:
        """Get list of available Telegram countries."""
        return await self._request("GET", "/tg/countries")

    async def tg_price(self, country: str) -> dict:
        """
        Get price for Telegram number in specific country.

        Args:
            country: Country code (e.g., 'US', 'IN')
        """
        return await self._request("GET", "/tg/price", params={"country": country})

    async def tg_order(self, country: str) -> dict:
        """
        Place an order for a Telegram number.

        Args:
            country: Country code (e.g., 'US', 'IN')
        """
        return await self._request("GET", "/tg/order", params={"country": country})

    async def tg_code(self, number: str) -> dict:
        """
        Get OTP code for an ordered Telegram number.

        Args:
            number: The phone number to check OTP for
        """
        return await self._request("GET", "/tg/code", params={"number": number})

    # ==================== WhatsApp Server 1 ====================

    async def wp_countries(self) -> dict:
        """Get list of available WhatsApp countries (Server 1)."""
        return await self._request("GET", "/wp/countries")

    async def wp_price(self, country: str) -> dict:
        """
        Get price for WhatsApp number in specific country (Server 1).

        Args:
            country: Country code (e.g., 'US', 'IN')
        """
        return await self._request("GET", "/wp/price", params={"country": country})

    async def wp_order(self, country: str) -> dict:
        """
        Place an order for a WhatsApp number (Server 1).

        Args:
            country: Country code (e.g., 'US', 'IN')
        """
        return await self._request("GET", "/wp/order", params={"country": country})

    async def wp_status(self, order_id: str) -> dict:
        """
        Check OTP status for a WhatsApp order (Server 1).

        Args:
            order_id: The order ID to check status for
        """
        return await self._request("GET", "/wp/status", params={"order_id": order_id})

    async def wp_cancel(self, order_id: str) -> dict:
        """
        Cancel a WhatsApp order and get refund (Server 1).

        Args:
            order_id: The order ID to cancel
        """
        return await self._request("GET", "/wp/cancel", params={"order_id": order_id})

    # ==================== WhatsApp Server 2 ====================

    async def wp2_countries(self) -> dict:
        """Get list of available WhatsApp countries (Server 2)."""
        return await self._request("GET", "/wp2/countries")

    async def wp2_price(self, country: str) -> dict:
        """
        Get price for WhatsApp number in specific country (Server 2).

        Args:
            country: Country code (e.g., 'US', 'IN')
        """
        return await self._request("GET", "/wp2/price", params={"country": country})

    async def wp2_order(self, country: str) -> dict:
        """
        Place an order for a WhatsApp number (Server 2).

        Args:
            country: Country code (e.g., 'US', 'IN')
        """
        return await self._request("GET", "/wp2/order", params={"country": country})

    async def wp2_status(self, order_id: str) -> dict:
        """
        Check OTP status for a WhatsApp order (Server 2).

        Args:
            order_id: The order ID to check status for
        """
        return await self._request("GET", "/wp2/status", params={"order_id": order_id})

    async def wp2_cancel(self, order_id: str) -> dict:
        """
        Cancel a WhatsApp order and get refund (Server 2).

        Args:
            order_id: The order ID to cancel
        """
        return await self._request("GET", "/wp2/cancel", params={"order_id": order_id})


# Singleton instance
api = OTPNowAPI()
