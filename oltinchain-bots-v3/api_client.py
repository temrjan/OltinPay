"""API client for interacting with OltinChain API with refresh token support."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID

import httpx

from config import config

logger = logging.getLogger(__name__)


class TokenStore:
    """Store tokens with expiration tracking."""

    def __init__(self):
        self.access_tokens: Dict[str, str] = {}
        self.refresh_tokens: Dict[str, str] = {}
        self.expires_at: Dict[str, datetime] = {}  # When access token expires

    def set_tokens(self, phone: str, access_token: str, refresh_token: str):
        """Store tokens for a phone number."""
        self.access_tokens[phone] = access_token
        self.refresh_tokens[phone] = refresh_token
        # Access token expires in 15 minutes, refresh 1 minute early
        self.expires_at[phone] = datetime.now(timezone.utc) + timedelta(minutes=14)

    def get_access_token(self, phone: str) -> Optional[str]:
        """Get access token if not expired."""
        return self.access_tokens.get(phone)

    def get_refresh_token(self, phone: str) -> Optional[str]:
        """Get refresh token."""
        return self.refresh_tokens.get(phone)

    def is_expired(self, phone: str) -> bool:
        """Check if access token is expired or about to expire."""
        expires = self.expires_at.get(phone)
        if not expires:
            return True
        return datetime.now(timezone.utc) >= expires

    def clear(self, phone: str):
        """Clear tokens for a phone number."""
        self.access_tokens.pop(phone, None)
        self.refresh_tokens.pop(phone, None)
        self.expires_at.pop(phone, None)


class APIClient:
    """HTTP client for OltinChain API with automatic token refresh."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._tokens = TokenStore()
        self._refresh_lock = asyncio.Lock()

    async def start(self) -> None:
        """Initialize HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=config.api_base_url,
            timeout=30.0,
        )

    async def stop(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()

    def _get_headers(self, phone: str) -> dict:
        """Get headers with auth token."""
        token = self._tokens.get_access_token(phone)
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    async def login(self, phone: str) -> bool:
        """Login and store both tokens."""
        try:
            response = await self._client.post(
                "/auth/login",
                json={
                    "phone": phone,
                    "password": config.bot_password,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Store BOTH tokens!
            self._tokens.set_tokens(
                phone=phone,
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
            )
            logger.info(f"Logged in: {phone}")
            return True
        except Exception as e:
            logger.error(f"Login failed for {phone}: {e}")
            return False

    async def refresh(self, phone: str) -> bool:
        """Refresh tokens using refresh_token."""
        async with self._refresh_lock:
            refresh_token = self._tokens.get_refresh_token(phone)
            if not refresh_token:
                logger.warning(f"No refresh token for {phone}, need re-login")
                return False

            try:
                response = await self._client.post(
                    "/auth/refresh",
                    json={"refresh_token": refresh_token},
                )
                response.raise_for_status()
                data = response.json()

                # Store new tokens
                self._tokens.set_tokens(
                    phone=phone,
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                )
                logger.info(f"Refreshed tokens for: {phone}")
                return True
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    # Refresh token also expired, need full re-login
                    logger.warning(
                        f"Refresh token expired for {phone}, re-logging in..."
                    )
                    self._tokens.clear(phone)
                    return await self.login(phone)
                logger.error(f"Refresh failed for {phone}: {e}")
                return False
            except Exception as e:
                logger.error(f"Refresh error for {phone}: {e}")
                return False

    async def ensure_valid_token(self, phone: str) -> bool:
        """Ensure we have a valid access token, refresh if needed."""
        if self._tokens.is_expired(phone):
            logger.debug(f"Token expired for {phone}, refreshing...")
            return await self.refresh(phone)
        return True

    async def _request_with_retry(
        self,
        phone: str,
        method: str,
        url: str,
        **kwargs,
    ) -> Optional[httpx.Response]:
        """Make request with automatic token refresh on 401."""
        # Ensure token is valid before request
        await self.ensure_valid_token(phone)

        headers = self._get_headers(phone)
        kwargs["headers"] = headers

        try:
            response = await self._client.request(method, url, **kwargs)

            # If 401, try to refresh and retry once
            if response.status_code == 401:
                logger.warning(f"Got 401 for {phone}, refreshing token...")
                if await self.refresh(phone):
                    # Retry with new token
                    kwargs["headers"] = self._get_headers(phone)
                    response = await self._client.request(method, url, **kwargs)

            return response
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    async def place_order(
        self,
        phone: str,
        side: str,
        price: Decimal,
        quantity: Decimal,
    ) -> Optional[UUID]:
        """Place a limit order."""
        response = await self._request_with_retry(
            phone,
            "POST",
            "/orderbook/orders",
            json={
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
            },
        )

        if not response:
            return None

        try:
            response.raise_for_status()
            data = response.json()

            # API returns {"order": {"id": ...}, "trades": [...]}
            order_data = data.get("order", {})
            order_id_str = order_data.get("id")

            if order_id_str:
                order_id = UUID(order_id_str)
                logger.info(f"Placed {side} order: {quantity} @ ${price} -> {order_id}")
                return order_id
            else:
                logger.error(f"No order id in response: {data}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Order placement failed: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            return None

    async def cancel_order(self, phone: str, order_id: UUID) -> bool:
        """Cancel an order."""
        response = await self._request_with_retry(
            phone,
            "DELETE",
            f"/orderbook/orders/{order_id}",
        )

        if not response:
            return False

        try:
            response.raise_for_status()
            logger.info(f"Cancelled order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Cancel failed for {order_id}: {e}")
            return False

    async def get_balance(self, phone: str) -> Dict[str, Decimal]:
        """Get wallet balance."""
        response = await self._request_with_retry(
            phone,
            "GET",
            "/wallet/balance",
        )

        if not response:
            return {}

        try:
            response.raise_for_status()
            data = response.json()

            balances = {}
            for item in data.get("balances", []):
                asset = item["asset"]
                available = Decimal(str(item["available"]))
                balances[asset] = available

            return balances
        except Exception as e:
            logger.error(f"Get balance failed: {e}")
            return {}

    async def get_order_status(self, phone: str, order_id: UUID) -> Optional[dict]:
        """Get order status."""
        response = await self._request_with_retry(
            phone,
            "GET",
            f"/orderbook/orders/{order_id}",
        )

        if not response:
            return None

        try:
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Get order status failed: {e}")
            return None


# Global instance
api_client = APIClient()
