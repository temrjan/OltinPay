"""Database operations for the bot system."""

import asyncio
import logging
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import AsyncGenerator, Optional, List
from uuid import UUID

import asyncpg

from config import config
from models import BotData, BotState, OrderData

logger = logging.getLogger(__name__)


class Database:
    """Database connection and operations."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(
            config.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
        logger.info("Database pool created")

    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection from the pool."""
        async with self.pool.acquire() as conn:
            yield conn

    # Bot operations
    async def get_all_bots(self) -> List[BotData]:
        """Get all MARKET MAKER bots with their states."""
        async with self.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    bs.id, bs.user_id, bs.bot_number, bs.level, bs.state,
                    bs.pending_order_id, bs.total_trades, bs.last_trade_at,
                    bs.state_changed_at, bs.created_at, bs.updated_at,
                    u.phone
                FROM bot_states bs
                JOIN users u ON u.id = bs.user_id
                WHERE bs.bot_type = 'market_maker' OR bs.bot_type IS NULL
                ORDER BY bs.bot_number
            """)

            bots = []
            for row in rows:
                bot = BotData(
                    id=row["id"],
                    user_id=row["user_id"],
                    bot_number=row["bot_number"],
                    level=row["level"],
                    state=BotState(row["state"]),
                    pending_order_id=row["pending_order_id"],
                    total_trades=row["total_trades"],
                    last_trade_at=row["last_trade_at"],
                    state_changed_at=row["state_changed_at"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    phone=row["phone"],
                )
                bots.append(bot)

            return bots

    async def get_bot_balances(self, user_id: UUID) -> tuple[Decimal, Decimal]:
        """Get bot balances (USD, OLTIN)."""
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT asset, available as total
                FROM balances
                WHERE user_id = $1
            """,
                user_id,
            )

            usd = Decimal("0")
            oltin = Decimal("0")

            for row in rows:
                if row["asset"] == "USD":
                    usd = row["total"]
                elif row["asset"] == "OLTIN":
                    oltin = row["total"]

            return usd, oltin

    async def update_bot_state(
        self,
        bot_id: UUID,
        state: BotState,
        pending_order_id: Optional[UUID] = None,
    ) -> None:
        """Update bot state."""
        async with self._lock:
            async with self.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE bot_states
                    SET state = $2,
                        pending_order_id = $3,
                        state_changed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = $1
                """,
                    bot_id,
                    state.value,
                    pending_order_id,
                )

    async def increment_bot_trades(self, bot_id: UUID) -> None:
        """Increment bot trade counter."""
        async with self.acquire() as conn:
            await conn.execute(
                """
                UPDATE bot_states
                SET total_trades = total_trades + 1,
                    last_trade_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1
            """,
                bot_id,
            )

    # Order operations
    async def get_order(self, order_id: UUID) -> Optional[OrderData]:
        """Get order by ID."""
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, side, price, quantity, filled_quantity,
                       status, created_at, bot_id
                FROM limit_orders
                WHERE id = $1
            """,
                order_id,
            )

            if not row:
                return None

            return OrderData(
                id=row["id"],
                user_id=row["user_id"],
                side=row["side"],
                price=row["price"],
                quantity=row["quantity"],
                filled_quantity=row["filled_quantity"],
                status=row["status"],
                created_at=row["created_at"],
                bot_id=row["bot_id"],
            )

    async def get_bot_open_orders(self, bot_id: UUID) -> List[OrderData]:
        """Get all open orders for a bot."""
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, side, price, quantity, filled_quantity,
                       status, created_at, bot_id
                FROM limit_orders
                WHERE bot_id = $1 AND status = 'open'
            """,
                bot_id,
            )

            return [
                OrderData(
                    id=row["id"],
                    user_id=row["user_id"],
                    side=row["side"],
                    price=row["price"],
                    quantity=row["quantity"],
                    filled_quantity=row["filled_quantity"],
                    status=row["status"],
                    created_at=row["created_at"],
                    bot_id=row["bot_id"],
                )
                for row in rows
            ]

    # Oracle operations
    async def save_oracle_price(self, price: Decimal, source: str) -> None:
        """Save oracle price to history."""
        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO oracle_prices (price, source)
                VALUES ($1, $2)
            """,
                price,
                source,
            )

    async def get_last_oracle_price(self) -> Optional[Decimal]:
        """Get last saved oracle price."""
        async with self.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT price FROM oracle_prices
                ORDER BY created_at DESC
                LIMIT 1
            """)
            return row["price"] if row else None

    # Rebalance operations
    async def save_rebalance(
        self,
        bot_id: UUID,
        imbalance_pct: Decimal,
        usd_before: Decimal,
        oltin_before: Decimal,
        action_type: str,
        market_order_side: Optional[str],
        market_order_value: Optional[Decimal],
        usd_after: Decimal,
        oltin_after: Decimal,
    ) -> None:
        """Save rebalance history."""
        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO rebalance_history (
                    bot_id, imbalance_pct, usd_before, oltin_before,
                    action_type, market_order_side, market_order_value,
                    usd_after, oltin_after
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                bot_id,
                imbalance_pct,
                usd_before,
                oltin_before,
                action_type,
                market_order_side,
                market_order_value,
                usd_after,
                oltin_after,
            )

    # Generic query methods for Active Traders
    async def execute(self, query: str, *args) -> None:
        """Execute a query without returning results."""
        async with self.acquire() as conn:
            await conn.execute(query, *args)

    async def fetch_all(self, query: str, *args) -> List[dict]:
        """Fetch all rows as list of dicts."""
        async with self.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetch_one(self, query: str, *args) -> Optional[dict]:
        """Fetch a single row as dict."""
        async with self.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None


# Global database instance
db = Database()
