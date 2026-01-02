"""Bot class with state machine logic.

Terminology:
- RED = Ask/Sell side (продажа)
- GREEN = Bid/Buy side (покупка)
"""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from api_client import api_client
from config import config
from database import db
from level_manager import level_manager
from models import BotData, BotState, OrderSide
from order_queue import order_queue

logger = logging.getLogger(__name__)


class Bot:
    """Market making bot with state machine."""

    def __init__(self, data: BotData):
        self.data = data
        self._oracle_price: Decimal = Decimal("250")

    @property
    def id(self) -> UUID:
        return self.data.id

    @property
    def level(self) -> int:
        return self.data.level

    @property
    def state(self) -> BotState:
        return self.data.state

    @property
    def phone(self) -> str:
        return self.data.phone

    def set_oracle_price(self, price: Decimal) -> None:
        """Update oracle price reference."""
        self._oracle_price = price

    async def refresh_balances(self) -> None:
        """Refresh balances from database."""
        usd, oltin = await db.get_bot_balances(self.data.user_id)
        self.data.usd_balance = usd
        self.data.oltin_balance = oltin

    def calculate_imbalance(self) -> Decimal:
        """Calculate balance imbalance (-0.5 to +0.5)."""
        usd_value = self.data.usd_balance
        oltin_value = self.data.oltin_balance * self._oracle_price
        total_value = usd_value + oltin_value

        if total_value == 0:
            return Decimal("0")

        oltin_ratio = oltin_value / total_value
        return oltin_ratio - Decimal("0.5")

    async def initialize(self) -> bool:
        """Initialize bot - login and set initial state."""
        success = await api_client.login(self.phone)
        if not success:
            logger.error(f"Bot {self.data.bot_number} login failed")
            return False

        await self.refresh_balances()

        # Even bots start RED (sell), odd bots start GREEN (buy)
        if self.data.state == BotState.IDLE:
            if self.data.bot_number % 2 == 0:
                await self.place_red_order()  # Sell
            else:
                await self.place_green_order()  # Buy

        state_name = (
            "RED" if self.state in [BotState.RED, BotState.WHITE_ASK] else "GREEN"
        )
        logger.info(f"Bot {self.data.bot_number} initialized: {state_name}")
        return True

    async def tick(self) -> None:
        """Process one tick of bot logic."""
        try:
            await self.refresh_balances()

            if self.state in [
                BotState.RED,
                BotState.WHITE_ASK,
                BotState.WHITE_BID,
                BotState.GREEN,
            ]:
                await self._check_order_status()

            elif self.state in [BotState.RED_DONE, BotState.GREEN_ASK]:
                # RED (sell) filled → place GREEN (buy)
                await self.place_green_order()

            elif self.state in [BotState.GREEN_DONE, BotState.GREEN_BID]:
                # GREEN (buy) filled → place RED (sell)
                await self.place_red_order()

            elif self.state == BotState.ERROR:
                await self._recover_from_error()

        except Exception as e:
            logger.error(f"Bot {self.data.bot_number} tick error: {e}")
            await self._set_state(BotState.ERROR)

    async def _check_order_status(self) -> None:
        """Check if pending order was filled or needs replacement."""
        if not self.data.pending_order_id:
            if self.state in [BotState.RED, BotState.WHITE_ASK]:
                await self.place_red_order()
            else:
                await self.place_green_order()
            return

        order = await db.get_order(self.data.pending_order_id)
        if not order:
            logger.warning(f"Bot {self.data.bot_number}: Order not found")
            await self._set_state(BotState.ERROR)
            return

        if order.status == "filled":
            await db.increment_bot_trades(self.id)

            if self.state in [BotState.RED, BotState.WHITE_ASK]:
                logger.info(f"Bot {self.data.bot_number}: RED filled → GREEN")
                await self._set_state(BotState.RED_DONE)
            else:
                logger.info(f"Bot {self.data.bot_number}: GREEN filled → RED")
                await self._set_state(BotState.GREEN_DONE)

        elif order.status == "cancelled":
            if self.state in [BotState.RED, BotState.WHITE_ASK]:
                await self.place_red_order()
            else:
                await self.place_green_order()

        else:
            await self._check_price_deviation(order)

    async def _check_price_deviation(self, order) -> None:
        """Check if order price deviates too much from oracle."""
        is_red = self.state in [BotState.RED, BotState.WHITE_ASK]
        side = OrderSide.SELL if is_red else OrderSide.BUY
        expected = level_manager.calculate_level_price(
            self._oracle_price, self.level, side
        )

        deviation = abs(order.price - expected.price) / expected.price

        if deviation > config.max_price_deviation_pct:
            color = "RED" if is_red else "GREEN"
            logger.info(
                f"Bot {self.data.bot_number}: {color} deviation {deviation:.1%} "
                f"(${order.price} → ${expected.price}), replacing"
            )

            success = await self.cancel_pending_order()
            if not success:
                logger.warning(
                    f"Bot {self.data.bot_number}: Failed to cancel for replacement"
                )
                return

            if is_red:
                await self.place_red_order()
            else:
                await self.place_green_order()

    async def place_red_order(self) -> None:
        """Place RED (sell/ask) order."""
        level_price = level_manager.calculate_level_price(
            self._oracle_price, self.level, OrderSide.SELL
        )

        quantity = level_manager.get_order_quantity(
            self.level,
            OrderSide.SELL,
            self._oracle_price,
            self.data.usd_balance,
            self.data.oltin_balance,
        )

        if quantity <= 0:
            logger.warning(f"Bot {self.data.bot_number}: Insufficient OLTIN for RED")
            return

        op_id = await order_queue.enqueue(
            "place_order",
            self.id,
            phone=self.phone,
            side="sell",
            price=level_price.price,
            quantity=quantity,
        )

        result = await order_queue.wait_for_result(op_id)
        if result and result.result:
            order_id = result.result.get("order_id")
            if order_id:
                await self._set_state(BotState.RED, order_id)
                logger.info(
                    f"Bot {self.data.bot_number}: RED {quantity} @ ${level_price.price}"
                )
            else:
                logger.error(f"Bot {self.data.bot_number}: RED order failed")

    async def place_green_order(self) -> None:
        """Place GREEN (buy/bid) order."""
        level_price = level_manager.calculate_level_price(
            self._oracle_price, self.level, OrderSide.BUY
        )

        quantity = level_manager.get_order_quantity(
            self.level,
            OrderSide.BUY,
            self._oracle_price,
            self.data.usd_balance,
            self.data.oltin_balance,
        )

        if quantity <= 0:
            logger.warning(f"Bot {self.data.bot_number}: Insufficient USD for GREEN")
            return

        op_id = await order_queue.enqueue(
            "place_order",
            self.id,
            phone=self.phone,
            side="buy",
            price=level_price.price,
            quantity=quantity,
        )

        result = await order_queue.wait_for_result(op_id)
        if result and result.result:
            order_id = result.result.get("order_id")
            if order_id:
                await self._set_state(BotState.GREEN, order_id)
                logger.info(
                    f"Bot {self.data.bot_number}: GREEN {quantity} @ ${level_price.price}"
                )
            else:
                logger.error(f"Bot {self.data.bot_number}: GREEN order failed")

    async def cancel_pending_order(self) -> bool:
        """Cancel the pending order if exists."""
        if not self.data.pending_order_id:
            return True

        op_id = await order_queue.enqueue(
            "cancel_order",
            self.id,
            phone=self.phone,
            order_id=self.data.pending_order_id,
        )

        result = await order_queue.wait_for_result(op_id)
        success = result and result.result and result.result.get("success", False)

        if success:
            self.data.pending_order_id = None

        return success

    async def _set_state(
        self, state: BotState, pending_order_id: Optional[UUID] = None
    ) -> None:
        """Update bot state."""
        self.data.state = state
        self.data.pending_order_id = pending_order_id
        await db.update_bot_state(self.id, state, pending_order_id)

    async def _recover_from_error(self) -> None:
        """Attempt to recover from error state."""
        logger.info(f"Bot {self.data.bot_number}: Recovering...")

        await self.cancel_pending_order()
        await self.refresh_balances()

        if self.data.bot_number % 2 == 0:
            await self.place_red_order()
        else:
            await self.place_green_order()
