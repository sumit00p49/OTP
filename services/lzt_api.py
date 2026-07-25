"""
LZT Market API client (https://prod-api.lzt.market).

Endpoints used:
- GET  /me                             -> seller profile + balance
- GET  /telegram?country[]=IN&...      -> search accounts with filters
- POST /{item_id}/fast-buy             -> atomic purchase (with price guard)
- GET  /{item_id}/telegram-login-code  -> fetch live OTP
- GET  /{item_id}                      -> full item/login data

FILTERS (confirmed working):
  nsb=1               -> No spam block (critical for OTP!)
  sb=1                -> Has spam block
  telegram_password=0 -> No 2FA password
  telegram_password=1 -> Has 2FA password
  eg=1                -> Has email/Gmail linked
  origin[]=resale     -> Account origin type
  not_sold_before=1   -> Never sold before
  telegram_premium=1  -> Has Telegram Premium
  pmax=0.15           -> Max price in USD
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
                # Rate limited - wait and retry
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
        """GET /me - seller profile + balance."""
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
        Search Telegram accounts with FULL filters applied.
        
        Args:
            country: 2-letter country code
            pmax: Maximum price in USD
            extra_filters: EFFECTIVE filters (should come from get_effective_filters())
                          Includes: nsb, telegram_password, eg, origin[], etc.
        
        The filters are sent as query params to LZT API exactly as specified.
        """
        country = _fix_country_code(country)

        params = {
            "country[]": country,
            "order_by": "price_to_up",
        }
        if pmax is not None:
            params["pmax"] = str(pmax)

        # Apply ALL effective filters
        # IMPORTANT: aiohttp handles param serialization. Pass values as-is (int/str)
        # LZT API expects: nsb=1, telegram_password=0, eg=1 as integers in query string
        if extra_filters and isinstance(extra_filters, dict):
            for key, value in extra_filters.items():
                # Keep numeric values as int, strings as-is
                if isinstance(value, (int, float)):
                    params[key] = value
                else:
                    params[key] = str(value)

        logger.info("LZT SEARCH: country=%s, params=%s", country, params)
        result = await self._request("GET", "/telegram", params=params)
        items = result.get("items", [])
        if isinstance(items, dict):
            items = list(items.values())
        items = items if isinstance(items, list) else []
        logger.info("LZT SEARCH returned %d items for %s", len(items), country)
        return items

    async def get_stock_count(self, country: str = "IN", pmax: float = None, extra_filters: dict = None) -> int:
        """
        Get REAL stock count for a country with ALL filters applied.
        Uses same filters as purchase to ensure accurate count (no fake numbers).
        """
        country = _fix_country_code(country)
        params = {
            "country[]": country,
            "order_by": "price_to_up",
        }
        if pmax is not None:
            params["pmax"] = str(pmax)
        if extra_filters and isinstance(extra_filters, dict):
            for key, value in extra_filters.items():
                if isinstance(value, (int, float)):
                    params[key] = value
                else:
                    params[key] = str(value)

        try:
            result = await self._request("GET", "/telegram", params=params)
            # Use totalItems for accurate count
            total = result.get("totalItems", result.get("total_items", 0))
            if not total:
                items = result.get("items", [])
                if isinstance(items, dict):
                    total = len(items)
                elif isinstance(items, list):
                    total = len(items)
            return int(total)
        except Exception as e:
            logger.warning("Stock count failed for %s: %s", country, e)
            return 0

    async def get_stock_debug(self, country: str = "IN", pmax: float = None, extra_filters: dict = None) -> dict:
        """
        Diagnostic: return the EXACT params sent + the raw total the API reports,
        so the admin can compare the bot's query against the LZT store view.
        """
        country = _fix_country_code(country)
        params = {"country[]": country, "order_by": "price_to_up"}
        if pmax is not None:
            params["pmax"] = str(pmax)
        if extra_filters and isinstance(extra_filters, dict):
            for key, value in extra_filters.items():
                params[key] = value if isinstance(value, (int, float)) else str(value)

        info = {"params": dict(params), "total": 0, "items_on_page": 0, "error": ""}
        try:
            result = await self._request("GET", "/telegram", params=params)
            total = result.get("totalItems", result.get("total_items", 0))
            items = result.get("items", [])
            if isinstance(items, dict):
                items = list(items.values())
            info["items_on_page"] = len(items) if isinstance(items, list) else 0
            info["total"] = int(total) if total else info["items_on_page"]
        except Exception as e:
            info["error"] = str(e)
        return info

    async def buy(self, item_id, price: float = None, currency: str = None) -> dict:
        """POST /{item_id}/fast-buy - atomic purchase with optional price guard."""
        data = {}
        if price is not None:
            data["price"] = price
        if currency:
            data["currency"] = currency
        return await self._request("POST", f"/{item_id}/fast-buy", data=data or None)

    async def get_item(self, item_id) -> dict:
        """GET /{item_id} - full item details (login data after purchase)."""
        return await self._request("GET", f"/{item_id}")

    async def verify_account_before_buy(self, item: dict) -> tuple[bool, str]:
        """
        Light safety check before buying.
        
        The search already filters with spam=no & nsb=1, so results should be
        clean. This is just a backup to catch anything obvious in the title.
        We trust the search filter — only reject on CLEAR spam block in title.
        
        Returns: (is_valid, reason)
        """
        title = str(item.get("title", "") or "").lower()
        title_en = str(item.get("title_en", "") or "").lower()
        full_title = title + " " + title_en
        
        # Only reject on OBVIOUS spam block words in title
        spam_keywords = [
            "permanent spamblock", "spamblock untill", "spamblock until",
            "spam block by geo", "спамблок",
        ]
        for kw in spam_keywords:
            if kw in full_title:
                return False, f"Title has '{kw}'"
        
        # Already sold
        if item.get("sold") is True or item.get("canBuy") is False:
            return False, "Already sold"
        
        # Trust the search filter (spam=no) — account is clean
        return True, "OK"

    async def get_telegram_login_code(self, item_id) -> Optional[str]:
        """
        Request Telegram login code for a purchased account.
        GET /{item_id}/telegram-login-code
        Response: {"item": {...}, "codes": [{"code": "12345", ...}]}
        """
        try:
            result = await self._request("GET", f"/{item_id}/telegram-login-code")
            logger.info("telegram-login-code for %s: keys=%s", item_id, list(result.keys()))

            # PRIMARY: codes array
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

    async def get_telegram_active_sessions(self, item_id) -> list:
        """
        Get active sessions/devices for a purchased Telegram account.
        
        LZT API mirrors web: GET /{item_id}/telegram-active-sessions
        If that fails, try GET /{item_id} and check for sessions data.
        
        Returns list of sessions: [{"device": "...", "location": "...", "app": "...", "active": "..."}, ...]
        """
        try:
            # Primary: dedicated endpoint
            result = await self._request("GET", f"/{item_id}/telegram-active-sessions")
            logger.info("active-sessions for %s: keys=%s", item_id, list(result.keys()))

            sessions = result.get("sessions", [])
            if not sessions:
                sessions = result.get("authorizations", [])
            if not sessions:
                # Try nested under "item"
                item = result.get("item", {})
                sessions = item.get("sessions", item.get("authorizations", []))

            return self._parse_sessions(sessions)

        except LZTAPIError as e:
            # Fallback: try validation endpoint
            logger.info("active-sessions endpoint failed (%s), trying validate...", e.message)
            try:
                result = await self._request("GET", f"/{item_id}/check-account")
                sessions = result.get("sessions", result.get("authorizations", []))
                if sessions:
                    return self._parse_sessions(sessions)
            except Exception:
                pass

            return []

    async def terminate_single_session(self, item_id, session_hash: str) -> bool:
        """
        Terminate a SINGLE specific session by its hash.
        
        LZT API: POST /{item_id}/telegram-reset-auth?hash={session_hash}
        Only removes that one device, others remain active.
        
        Returns True if successful.
        """
        try:
            result = await self._request(
                "POST",
                f"/{item_id}/telegram-reset-auth",
                data={"hash": session_hash},
            )
            logger.info("single reset-auth for %s hash=%s: %s", item_id, session_hash, result)
            return True
        except LZTAPIError as e:
            logger.warning("single reset-auth failed for %s hash=%s: %s", item_id, session_hash, e.message)
            return False

    async def terminate_all_sessions(self, item_id) -> bool:
        """
        Terminate/reset all other sessions on a purchased Telegram account.
        
        LZT API: POST /{item_id}/telegram-reset-auth
        This removes all devices except the current login session.
        
        Returns True if successful.
        """
        try:
            result = await self._request("POST", f"/{item_id}/telegram-reset-auth")
            logger.info("reset-auth for %s: %s", item_id, result)
            return True
        except LZTAPIError as e:
            logger.warning("telegram-reset-auth failed for %s: %s", item_id, e.message)
            return False

    @staticmethod
    def _parse_sessions(raw_sessions) -> list:
        """Parse raw session data into clean format."""
        parsed = []
        if not raw_sessions or not isinstance(raw_sessions, list):
            return parsed

        for s in raw_sessions:
            if isinstance(s, dict):
                session = {
                    "device": s.get("device_model", s.get("device", "Unknown")),
                    "platform": s.get("platform", s.get("system_version", "")),
                    "app": s.get("app_name", s.get("app_version", "")),
                    "ip": s.get("ip", s.get("ip_address", "")),
                    "location": s.get("country", s.get("region", s.get("location", ""))),
                    "active": s.get("date_active", s.get("last_active", "")),
                    "current": s.get("current", s.get("is_current", False)),
                    "hash": s.get("hash", ""),
                }
                parsed.append(session)
            elif isinstance(s, str):
                parsed.append({"device": s, "platform": "", "app": "", "ip": "", "location": "", "active": "", "current": False, "hash": ""})

        return parsed

    @staticmethod
    def extract_account_data(payload: dict) -> dict:
        """
        Normalize account details from a buy/item response.
        """
        item = payload.get("item", payload)
        login_data = item.get("loginData", {}) or {}

        # Phone number
        phone = (
            item.get("telegram_formatted_phone")
            or item.get("telegram_phone")
            or ""
        )

        if not phone:
            login_field = item.get("login") or ""
            clean = login_field.replace("+", "").replace(" ", "")
            if clean.isdigit() and len(clean) <= 15:
                phone = login_field

        if not phone:
            phone = _extract_phone_from_title(item.get("title", ""))

        if not phone:
            phone = "N/A"

        # Auth key
        auth_key = ""
        login_field = item.get("login") or ""
        if len(login_field) > 30:
            auth_key = login_field

        # 2FA Password
        password = login_data.get("password") or login_data.get("encodedPassword") or ""

        # Username
        username = item.get("telegram_username") or ""

        # Whether OTP is available
        otp_available = item.get("showGetTelegramCodeButton", False)

        # Email info
        email = item.get("email_login_data") or item.get("emailLoginData") or ""

        return {
            "item_id": str(item.get("item_id", item.get("id", ""))),
            "phone": phone,
            "auth_key": auth_key,
            "password": password,
            "2fa": password,
            "username": username,
            "otp_available": otp_available,
            "has_tdata": bool(item.get("telegram_json")),
            "email": email if isinstance(email, str) else "",
        }


def _extract_phone_from_title(title: str) -> str:
    """Try to extract a phone number from the item title."""
    if not title:
        return ""
    import re
    match = re.search(r'(\+?\d[\d\s]{8,15})', title)
    if match:
        phone = match.group(1).replace(" ", "")
        if 8 <= len(phone.replace("+", "")) <= 15:
            return phone
    return ""


def _fix_country_code(code: str) -> str:
    """Fix common country code mistakes. LZT uses ISO 3166-1 alpha-2."""
    fixes = {
        "UK": "GB",
        "EN": "GB",
        "KO": "KR",
    }
    upper = code.upper().strip()
    return fixes.get(upper, upper)


# Singleton
lzt_api = LZTMarketAPI()
