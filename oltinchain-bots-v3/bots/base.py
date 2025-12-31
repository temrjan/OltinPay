"""Base bot class."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from clients.api_client import APIClient
from clients.oracle_client import CycleState

logger = logging.getLogger(__name__)


@dataclass
class Order:
    """Order to place."""

    side: str  # "buy" or "sell"
    price: Decimal
    quantity: Decimal


@dataclass
class BotState:
    """Bot internal state."""

    balance_usd: Decimal = Decimal("0")
    balance_oltin: Decimal = Decimal("0")
    active_orders: list[dict[str, Any]] = field(default_factory=list)
    orders_placed: int = 0
    orders_filled: int = 0
    total_volume_usd: Decimal = Decimal("0")


class BaseBot(ABC):
    """Base class for all trading bots."""

    bot_type: str = "base"

    def __init__(
        self,
        bot_id: str,
        api_client: APIClient,
        initial_usd: Decimal,
        initial_oltin: Decimal,
    ):
        self.bot_id = bot_id
        self.api = api_client
        self.state = BotState(
            balance_usd=initial_usd,
            balance_oltin=initial_oltin,
        )
        self.logger = logging.getLogger(f"bot.{bot_id}")

    @property
    def balance_usd(self) -> Decimal:
        """Current USD balance."""
        return self.state.balance_usd

    @property
    def balance_oltin(self) -> Decimal:
        """Current OLTIN balance."""
        return self.state.balance_oltin

    async def sync_balance(self):
        """Sync balance from API."""
        try:
            balance = await self.api.get_balance(self.bot_id)
            self.state.balance_usd = balance.get("usd", Decimal("0"))
            self.state.balance_oltin = balance.get("oltin", Decimal("0"))
        except Exception as e:
            self.logger.warning(f"Failed to sync balance: {e}")

    async def sync_orders(self):
        """Sync active orders from API."""
        try:
            orders = await self.api.get_my_orders(self.bot_id, status="open")
            self.state.active_orders = orders
        except Exception as e:
            self.logger.warning(f"Failed to sync orders: {e}")

    async def cancel_old_orders(self, max_age_seconds: int = 300):
        """Cancel orders older than max_age_seconds."""
        now = datetime.now(timezone.utc)

        for order in self.state.active_orders:
            created_at = order.get("created_at", "")
            if not created_at:
                continue

            try:
                # Parse datetime string
                order_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                
                # Add UTC timezone if offset-naive
                if order_time.tzinfo is None:
                    order_time = order_time.replace(tzinfo=timezone.utc)
                
                age = (now - order_time).total_seconds()

                if age > max_age_seconds:
                    order_id = UUID(order["id"])
                    await self.api.cancel_order(self.bot_id, order_id)
                    self.logger.info(f"Cancelled old order {order_id}")
            except Exception as e:
                self.logger.warning(f"Failed to cancel order: {e}")

    async def place_order(self, order: Order) -> dict[str, Any]:
        """Place an order via API."""
        result = await self.api.place_order(
            self.bot_id,
            order.side,
            order.price,
            order.quantity,
        )

        if "error" not in result:
            self.state.orders_placed += 1
            self.logger.info(
                f"Placed {order.side} order: {order.quantity} @ ${order.price}"
            )

        return result

    @abstractmethod
    async def generate_orders(
        self,
        oracle_price: Decimal,
        market_price: Decimal | None,
        cycle_state: CycleState,
    ) -> list[Order]:
        """Generate orders based on market state."""
        pass

    async def tick(
        self,
        oracle_price: Decimal,
        market_price: Decimal | None,
        cycle_state: CycleState,
    ):
        """Execute one trading cycle."""
        try:
            # Sync state
            await self.sync_balance()
            await self.sync_orders()

            # Cancel old orders
            await self.cancel_old_orders()

            # Generate new orders
            orders = await self.generate_orders(
                oracle_price, market_price, cycle_state
            )

            # Place orders
            for order in orders:
                await self.place_order(order)

        except Exception as e:
            self.logger.error(f"Tick error: {e}")
