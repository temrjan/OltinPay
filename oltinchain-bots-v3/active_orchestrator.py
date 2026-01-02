"""
Active Orchestrator - Manages queue rotation for Active Traders.

Coordinates 20 Active Trader bots in an alternating pattern:
RED1 -> GREEN1 -> RED2 -> GREEN2 -> ... -> RED10 -> GREEN10 -> repeat

Bots are pre-created via SQL migration (003_create_active_traders.sql).
This orchestrator just loads them and starts trading.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Optional

import httpx

from config import config
from active_trader import ActiveTrader
from api_client import api_client  # Global instance
from database import Database

logger = logging.getLogger(__name__)


class ActiveOrchestrator:
    """
    Orchestrates Active Trader bots in a round-robin queue.

    Queue pattern: RED1 -> GREEN1 -> RED2 -> GREEN2 -> ...
    Each bot executes one trade, then waits for full rotation.
    """

    def __init__(
        self,
        db: Database,
        oracle,  # OracleService instance
    ):
        self.db = db
        self.oracle = oracle
        self.traders: list[ActiveTrader] = []
        self.current_index = 0
        self.cycle_delay_sec = 5  # Delay between trades
        self.is_running = False
        self._http_client: Optional[httpx.AsyncClient] = None
        self.startup_delay = 0  # Delay before starting (set by main.py)

    async def _get_orderbook(self) -> tuple[Decimal, Decimal] | None:
        """Get best bid and ask from orderbook API."""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(
                base_url=config.api_base_url,
                timeout=10.0,
            )

        try:
            response = await self._http_client.get("/orderbook")
            response.raise_for_status()
            data = response.json()

            bids = data.get("bids", [])
            asks = data.get("asks", [])

            if bids and asks:
                best_bid = max(Decimal(b["price"]) for b in bids)
                best_ask = min(Decimal(a["price"]) for a in asks)
                return best_bid, best_ask

        except Exception as e:
            logger.error(f"Failed to get orderbook: {e}")

        return None

    async def load_traders(self) -> None:
        """Load Active Traders from database."""
        rows = await self.db.fetch_all(
            """
            SELECT
                aq.bot_id,
                aq.side,
                aq.position,
                u.phone
            FROM active_bot_queue aq
            JOIN bot_states bs ON aq.bot_id = bs.user_id
            JOIN users u ON bs.user_id = u.id
            WHERE aq.is_active = true
            ORDER BY aq.position, aq.side
            """
        )

        self.traders = []

        for row in rows:
            trader = ActiveTrader(
                user_id=row["bot_id"],
                phone=row["phone"],
                db=self.db,
                api_client=api_client,
                side=row["side"],
                position=row["position"],
            )
            self.traders.append(trader)

        # Sort for alternating pattern: RED1, GREEN1, RED2, GREEN2, ...
        self.traders.sort(key=lambda t: (t.position, 0 if t.side == "red" else 1))

        logger.info(f"Active traders loaded: {len(self.traders)}")

    async def login_all_traders(self) -> int:
        """
        Login all traders at startup.
        Returns count of successful logins.
        """
        if not self.traders:
            return 0

        success_count = 0
        logger.info(f"Logging in {len(self.traders)} Active Traders...")

        for trader in self.traders:
            try:
                # Login via api_client
                if await api_client.login(trader.phone):
                    trader._logged_in = True
                    success_count += 1
                    logger.debug(f"Logged in: {trader.phone}")
                else:
                    logger.warning(f"Login failed: {trader.phone}")
            except Exception as e:
                logger.error(f"Login error for {trader.phone}: {e}")

            # Rate limiting: 5 logins per minute = 12 seconds between logins
            # Using 13 seconds to be safe
            await asyncio.sleep(13)

        logger.info(
            f"Active Traders login complete: {success_count}/{len(self.traders)}"
        )
        return success_count

    async def run_cycle(self) -> None:
        """Execute one full rotation through all traders."""
        prices = await self._get_orderbook()
        if not prices:
            logger.warning("No orderbook prices available for Active Traders")
            return

        best_bid, best_ask = prices
        oracle_price = (best_bid + best_ask) / 2

        red_trades = 0
        green_trades = 0

        for trader in self.traders:
            if not self.is_running:
                break

            # Skip traders that aren't logged in
            if not trader._logged_in:
                continue

            try:
                order = await trader.execute_trade(best_bid, best_ask, oracle_price)
                if order:
                    if trader.side == "red":
                        red_trades += 1
                    else:
                        green_trades += 1
            except Exception as e:
                logger.error(f"Trader {trader.phone} cycle error: {e}")
                # Try to re-login on error
                trader._logged_in = False

            # Delay between trades to prevent rate limiting
            await asyncio.sleep(self.cycle_delay_sec)

        logger.info(
            f"Active cycle complete: RED={red_trades}, GREEN={green_trades}, Oracle=${oracle_price}"
        )

    async def run(self) -> None:
        """Main loop - continuously run cycles."""
        self.is_running = True

        # Wait for startup delay (to avoid rate limit collision with Market Maker logins)
        if self.startup_delay > 0:
            logger.info(
                f"Active Orchestrator waiting {self.startup_delay}s for Market Maker logins..."
            )
            await asyncio.sleep(self.startup_delay)

        # Load traders from database
        await self.load_traders()

        if not self.traders:
            logger.warning("No active traders found in database. Run migration first!")
            logger.warning(
                "Execute: psql -d oltinchain -f migrations/003_create_active_traders.sql"
            )
            return

        # Login all traders at startup (this takes ~5 minutes for 20 bots)
        logged_in = await self.login_all_traders()

        if logged_in == 0:
            logger.error(
                "No traders logged in! Check credentials and API availability."
            )
            return

        logger.info(f"Active Orchestrator started with {logged_in} traders")

        cycle_num = 0
        while self.is_running:
            cycle_num += 1
            logger.info(f"=== Active Cycle {cycle_num} ===")

            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Cycle {cycle_num} error: {e}")

            # Pause between full cycles
            await asyncio.sleep(10)

    async def stop(self) -> None:
        """Stop the orchestrator."""
        self.is_running = False
        if self._http_client:
            await self._http_client.aclose()
        logger.info("Active Orchestrator stopped")
