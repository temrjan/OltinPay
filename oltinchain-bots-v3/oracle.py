"""Oracle price service."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx

from config import config
from database import db

logger = logging.getLogger(__name__)


class OracleService:
    """Provides reference price for the market."""

    def __init__(self):
        self._cached_price: Optional[Decimal] = None
        self._cache_time: Optional[datetime] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Initialize the oracle service."""
        self._http_client = httpx.AsyncClient(
            base_url=config.api_base_url,
            timeout=10.0,
        )

    async def stop(self) -> None:
        """Stop the oracle service."""
        if self._http_client:
            await self._http_client.aclose()

    async def get_price(self) -> Decimal:
        """Get current oracle price."""
        # Check cache
        if self._is_cache_valid():
            return self._cached_price

        # Try to get fresh price
        price = await self._fetch_price()

        if price:
            self._cached_price = price
            self._cache_time = datetime.utcnow()
            return price

        # Fallback to cached or database
        if self._cached_price:
            logger.warning("Using stale cached price")
            return self._cached_price

        db_price = await db.get_last_oracle_price()
        if db_price:
            logger.warning("Using database cached price")
            self._cached_price = db_price
            return db_price

        # Ultimate fallback
        logger.error("No price available, using default")
        return Decimal("250.00")

    async def _fetch_price(self) -> Optional[Decimal]:
        """Fetch price from orderbook."""
        try:
            response = await self._http_client.get("/orderbook")
            response.raise_for_status()
            data = response.json()

            bids = data.get("bids", [])
            asks = data.get("asks", [])

            if bids and asks:
                # Bids are sorted descending - bids[0] is highest (best bid)
                best_bid = max(Decimal(b["price"]) for b in bids)

                # Asks may be sorted any way - find minimum (best ask)
                best_ask = min(Decimal(a["price"]) for a in asks)

                mid_price = (best_ask + best_bid) / 2

                logger.debug(
                    f"Oracle: bid=${best_bid}, ask=${best_ask}, mid=${mid_price}"
                )

                return mid_price.quantize(Decimal("0.01"))

            # If no orders, try last trade
            return await self._fetch_last_trade_price()

        except Exception as e:
            logger.error(f"Failed to fetch orderbook price: {e}")
            return None

    async def _fetch_last_trade_price(self) -> Optional[Decimal]:
        """Fetch last trade price as fallback."""
        try:
            response = await self._http_client.get("/orderbook/trades?limit=1")
            response.raise_for_status()
            data = response.json()

            if data:
                return Decimal(str(data[0]["price"]))
            return None

        except Exception as e:
            logger.error(f"Failed to fetch last trade price: {e}")
            return None

    def _is_cache_valid(self) -> bool:
        """Check if cached price is still valid."""
        if not self._cached_price or not self._cache_time:
            return False

        age = datetime.utcnow() - self._cache_time
        return age.total_seconds() < config.oracle_cache_ttl_sec

    def is_price_valid(self, price: Decimal) -> bool:
        """Check if price is within acceptable deviation."""
        if not self._cached_price:
            return price > 0

        deviation = abs(price - self._cached_price) / self._cached_price
        return deviation < config.max_price_deviation_pct


# Global instance
oracle = OracleService()
