"""Client for Price Oracle API."""

import logging
from dataclasses import dataclass
from decimal import Decimal

import httpx

from config import config

logger = logging.getLogger(__name__)


@dataclass
class CycleState:
    """Price Oracle cycle state."""

    cycle: int
    phase: str
    target_price: Decimal
    phase_progress: float
    volatility: float


class OracleClient:
    """Client for OltinChain Price Oracle."""

    def __init__(self):
        self.base_url = config.api_base_url
        self._client = httpx.AsyncClient(timeout=10.0)
        self._last_state: CycleState | None = None

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()

    async def get_price(self) -> Decimal:
        """Get current oracle price."""
        url = f"{self.base_url}/price/current"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return Decimal(str(data.get("price", "265")))
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            if self._last_state:
                return self._last_state.target_price
            return Decimal("265")

    async def get_cycle_state(self) -> CycleState:
        """Get current Wyckoff cycle state."""
        url = f"{self.base_url}/price/cycle"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()

            state = CycleState(
                cycle=data.get("current_cycle", 1),
                phase=data.get("phase", "markup"),
                target_price=Decimal(str(data.get("target_price", "265"))),
                phase_progress=data.get("phase_progress", 0.5),
                volatility=data.get("volatility", 0.01),
            )
            self._last_state = state
            return state

        except Exception as e:
            logger.error(f"Failed to get cycle: {e}")
            if self._last_state:
                return self._last_state
            return CycleState(
                cycle=1,
                phase="markup",
                target_price=Decimal("265"),
                phase_progress=0.5,
                volatility=0.01,
            )

    async def get_market_price(self) -> Decimal | None:
        """Get current market price from orderbook."""
        url = f"{self.base_url}/orderbook?depth=5"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()

            bids = data.get("bids", [])
            asks = data.get("asks", [])

            if bids and asks:
                best_bid = Decimal(str(bids[0]["price"]))
                best_ask = Decimal(str(asks[0]["price"]))
                return (best_bid + best_ask) / 2

            if bids:
                return Decimal(str(bids[0]["price"]))
            if asks:
                return Decimal(str(asks[0]["price"]))

            return None

        except Exception as e:
            logger.warning(f"Failed to get market price: {e}")
            return None
