"""Rebalancing guardian for bots."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict
from uuid import UUID

from config import config
from database import db
from bot import Bot
from models import BotState

logger = logging.getLogger(__name__)


class RebalanceGuardian:
    """Monitors and rebalances bots."""

    def __init__(self):
        self._last_rebalance: Dict[UUID, datetime] = {}
        self._rebalances_this_minute: int = 0
        self._minute_start: datetime = datetime.utcnow()

    async def check_bot(self, bot: Bot, oracle_price: Decimal) -> None:
        """Check if bot needs rebalancing."""
        bot.set_oracle_price(oracle_price)
        imbalance = abs(bot.calculate_imbalance())

        # Reset minute counter if needed
        now = datetime.utcnow()
        if (now - self._minute_start).total_seconds() >= 60:
            self._rebalances_this_minute = 0
            self._minute_start = now

        if imbalance < config.soft_threshold:
            # OK - no action needed
            return

        if imbalance < config.hard_threshold:
            # SOFT - just log for now, could adjust order placement
            logger.debug(f"Bot {bot.data.bot_number} soft imbalance: {imbalance:.1%}")
            return

        # Check if can rebalance
        if not self._can_rebalance(bot.id):
            return

        if imbalance < config.critical_threshold:
            # HARD - market order 25%
            await self._execute_rebalance(bot, config.hard_correction_pct, "hard")
        else:
            # CRITICAL - market order 50%
            await self._execute_rebalance(
                bot, config.critical_correction_pct, "critical"
            )

    def _can_rebalance(self, bot_id: UUID) -> bool:
        """Check if bot can perform rebalance."""
        # Check system-wide limit
        if self._rebalances_this_minute >= config.max_rebalances_per_minute:
            logger.debug("System rebalance limit reached")
            return False

        # Check bot cooldown
        last = self._last_rebalance.get(bot_id)
        if last:
            elapsed = (datetime.utcnow() - last).total_seconds()
            if elapsed < config.rebalance_cooldown_sec:
                return False

        return True

    async def _execute_rebalance(
        self,
        bot: Bot,
        correction_pct: Decimal,
        action_type: str,
    ) -> None:
        """Execute rebalancing for a bot."""
        logger.info(f"Bot {bot.data.bot_number}: Executing {action_type} rebalance")

        # Store before state
        usd_before = bot.data.usd_balance
        oltin_before = bot.data.oltin_balance
        imbalance = bot.calculate_imbalance()

        # Cancel pending order first
        await bot.cancel_pending_order()

        # Set rebalancing state
        await db.update_bot_state(bot.id, BotState.REBALANCING)

        # Calculate rebalance amount
        # Note: For now we just log - actual market orders need API support
        # In production, this would execute market order through order_queue

        usd_value = bot.data.usd_balance
        oltin_value = bot.data.oltin_balance * bot._oracle_price
        total_value = usd_value + oltin_value
        target_each = total_value / 2

        if imbalance < 0:
            # Too much USD - need to buy OLTIN
            deficit = target_each - oltin_value
            rebalance_value = deficit * correction_pct
            side = "buy"
            logger.info(
                f"Bot {bot.data.bot_number}: Would market buy ${rebalance_value:.2f}"
            )
        else:
            # Too much OLTIN - need to sell
            excess = oltin_value - target_each
            rebalance_value = excess * correction_pct
            side = "sell"
            logger.info(
                f"Bot {bot.data.bot_number}: Would market sell ${rebalance_value:.2f}"
            )

        # Refresh balances after (simulated) market order
        await bot.refresh_balances()

        # Save rebalance history
        await db.save_rebalance(
            bot_id=bot.id,
            imbalance_pct=imbalance * 100,
            usd_before=usd_before,
            oltin_before=oltin_before,
            action_type=action_type,
            market_order_side=side,
            market_order_value=rebalance_value if "rebalance_value" in dir() else None,
            usd_after=bot.data.usd_balance,
            oltin_after=bot.data.oltin_balance,
        )

        # Update tracking
        self._last_rebalance[bot.id] = datetime.utcnow()
        self._rebalances_this_minute += 1

        # Place new order
        if bot.data.bot_number % 2 == 0:
            await bot.place_red_order()
        else:
            await bot.place_green_order()


# Global instance
rebalancer = RebalanceGuardian()
