"""HTTP client for OltinChain API."""

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx

from config import config

logger = logging.getLogger(__name__)


class APIClient:
    """Client for OltinChain trading API."""

    def __init__(self):
        self.base_url = config.api_base_url
        self._client = httpx.AsyncClient(timeout=30.0)
        self._tokens: dict[str, str] = {}  # bot_id -> access_token

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()

    async def register_bot(self, phone: str, password: str) -> dict[str, Any]:
        """Register a new bot user."""
        url = f"{self.base_url}/auth/register"
        resp = await self._client.post(url, json={
            "phone": phone,
            "password": password,
        })

        if resp.status_code == 400:
            # Already exists, try login
            return await self.login(phone, password)

        resp.raise_for_status()
        data = resp.json()
        self._tokens[phone] = data["access_token"]
        return data

    async def login(self, phone: str, password: str) -> dict[str, Any]:
        """Login bot user."""
        url = f"{self.base_url}/auth/login"
        resp = await self._client.post(url, json={
            "phone": phone,
            "password": password,
        })
        resp.raise_for_status()
        data = resp.json()
        self._tokens[phone] = data["access_token"]
        return data

    def _get_headers(self, bot_id: str) -> dict[str, str]:
        """Get auth headers for bot."""
        token = self._tokens.get(bot_id)
        if not token:
            raise ValueError(f"Bot {bot_id} not authenticated")
        return {"Authorization": f"Bearer {token}"}

    async def place_order(
        self,
        bot_id: str,
        side: str,
        price: Decimal,
        quantity: Decimal,
    ) -> dict[str, Any]:
        """Place a limit order."""
        url = f"{self.base_url}/orderbook/orders"
        headers = self._get_headers(bot_id)

        resp = await self._client.post(
            url,
            headers=headers,
            json={
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
            },
        )

        if resp.status_code != 200:
            logger.warning(
                f"Order failed: {resp.status_code} - {resp.text}"
            )
            return {"error": resp.text}

        return resp.json()

    async def cancel_order(self, bot_id: str, order_id: UUID) -> dict[str, Any]:
        """Cancel an order."""
        url = f"{self.base_url}/orderbook/orders/{order_id}"
        headers = self._get_headers(bot_id)

        resp = await self._client.delete(url, headers=headers)
        if resp.status_code != 200:
            return {"error": resp.text}

        return resp.json()

    async def get_my_orders(
        self,
        bot_id: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get bot's orders."""
        url = f"{self.base_url}/orderbook/orders"
        if status:
            url += f"?status={status}"

        headers = self._get_headers(bot_id)
        resp = await self._client.get(url, headers=headers)

        if resp.status_code != 200:
            return []

        return resp.json().get("orders", [])

    async def get_orderbook(self, depth: int = 20) -> dict[str, Any]:
        """Get current orderbook."""
        url = f"{self.base_url}/orderbook?depth={depth}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def get_balance(self, bot_id: str) -> dict[str, Decimal]:
        """Get bot's balance."""
        url = f"{self.base_url}/wallet/balance"
        headers = self._get_headers(bot_id)

        try:
            resp = await self._client.get(url, headers=headers)
            if resp.status_code != 200:
                return {"usd": Decimal("0"), "oltin": Decimal("0")}

            data = resp.json()
            return {
                "usd": Decimal(str(data.get("usd", {}).get("available", "0"))),
                "oltin": Decimal(str(data.get("oltin", {}).get("available", "0"))),
            }
        except Exception as e:
            logger.warning(f"Failed to get balance: {e}")
            return {"usd": Decimal("0"), "oltin": Decimal("0")}
