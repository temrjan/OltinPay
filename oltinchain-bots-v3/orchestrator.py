"""Main orchestrator for the bot system.

Terminology:
- RED = Ask/Sell side (продажа)
- GREEN = Bid/Buy side (покупка)
"""

import asyncio
import logging
from decimal import Decimal
from typing import List
from uuid import UUID

from api_client import api_client
from bot import Bot
from config import config
from database import db
from models import BotState
from oracle import oracle
from order_queue import order_queue
from rebalancer import rebalancer

logger = logging.getLogger(__name__)


class Orchestrator:
    """Manages all market making bots."""

    def __init__(self):
        self.bots: List[Bot] = []
        self._running: bool = False
        self._initialized: bool = False
        self._last_system_rebalance: float = 0

    async def start(self) -> None:
        """Start the orchestrator."""
        logger.info("=" * 60)
        logger.info("OltinChain Market Making Bots v4 (State Machine)")
        logger.info("RED = Sell/Ask | GREEN = Buy/Bid")
        logger.info("=" * 60)

        await db.connect()
        await api_client.start()
        await oracle.start()
        await order_queue.start()

        order_queue.register_handler("place_order", self._handle_place_order)
        order_queue.register_handler("cancel_order", self._handle_cancel_order)

        await self._load_bots()

        self._running = True
        logger.info(f"Orchestrator started with {len(self.bots)} bots")

    async def stop(self) -> None:
        """Stop the orchestrator."""
        logger.info("Stopping orchestrator...")
        self._running = False

        await order_queue.stop()
        await oracle.stop()
        await api_client.stop()
        await db.close()

        logger.info("Orchestrator stopped")

    async def run(self) -> None:
        """Main run loop."""
        cycle = 0

        while self._running:
            try:
                cycle += 1
                oracle_price = await oracle.get_price()

                if cycle % 12 == 1:
                    stats = self._get_side_stats()
                    logger.info(
                        f"=== Cycle {cycle} | Oracle: ${oracle_price} | "
                        f"RED: {stats['red']} | GREEN: {stats['green']} ==="
                    )

                if not self._initialized:
                    await self._initialize_bots_slowly()
                    self._initialized = True
                    continue

                await self._check_system_balance(oracle_price)

                for bot in self.bots:
                    if not self._running:
                        break

                    try:
                        bot.set_oracle_price(oracle_price)
                        await bot.tick()
                        await rebalancer.check_bot(bot, oracle_price)

                    except Exception as e:
                        logger.error(f"Bot {bot.data.bot_number} error: {e}")

                await asyncio.sleep(config.order_check_interval_sec)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(5)

    def _get_side_stats(self) -> dict:
        """Get count of bots on each side."""
        red = 0  # Sell/Ask
        green = 0  # Buy/Bid

        for bot in self.bots:
            if bot.state in [
                BotState.RED,
                BotState.WHITE_ASK,
                BotState.GREEN_DONE,
                BotState.GREEN_BID,
            ]:
                red += 1
            elif bot.state in [
                BotState.GREEN,
                BotState.WHITE_BID,
                BotState.RED_DONE,
                BotState.GREEN_ASK,
            ]:
                green += 1

        return {"red": red, "green": green}

    async def _check_system_balance(self, oracle_price: Decimal) -> None:
        """Ensure roughly equal bots on each side (RED/GREEN)."""
        import time

        now = time.time()
        if now - self._last_system_rebalance < config.system_rebalance_cooldown_sec:
            return

        red_bots = []  # Sell side
        green_bots = []  # Buy side

        for bot in self.bots:
            if bot.state in [BotState.RED, BotState.WHITE_ASK]:
                red_bots.append(bot)
            elif bot.state in [BotState.GREEN, BotState.WHITE_BID]:
                green_bots.append(bot)
            elif bot.state in [BotState.RED_DONE, BotState.GREEN_ASK]:
                green_bots.append(bot)  # About to go GREEN
            elif bot.state in [BotState.GREEN_DONE, BotState.GREEN_BID]:
                red_bots.append(bot)  # About to go RED

        total = len(red_bots) + len(green_bots)
        if total == 0:
            return

        red_ratio = len(red_bots) / total

        if config.system_balance_min <= red_ratio <= config.system_balance_max:
            return

        self._last_system_rebalance = now
        target_red = total // 2

        if red_ratio > float(config.system_balance_max):
            # Too many RED → move some to GREEN
            excess = len(red_bots) - target_red
            logger.info(
                f"Rebalance: {len(red_bots)} RED / {len(green_bots)} GREEN → moving {excess} to GREEN"
            )

            for bot in red_bots:
                await bot.refresh_balances()
            red_bots.sort(key=lambda b: b.data.oltin_balance)

            for bot in red_bots[:excess]:
                logger.info(f"Bot {bot.data.bot_number}: RED → GREEN")
                await bot.cancel_pending_order()
                bot.set_oracle_price(oracle_price)
                await bot.place_green_order()
                await asyncio.sleep(0.2)

        elif red_ratio < float(config.system_balance_min):
            # Too many GREEN → move some to RED
            excess = len(green_bots) - target_red
            logger.info(
                f"Rebalance: {len(red_bots)} RED / {len(green_bots)} GREEN → moving {excess} to RED"
            )

            for bot in green_bots:
                await bot.refresh_balances()
            green_bots.sort(key=lambda b: b.data.oltin_balance, reverse=True)

            for bot in green_bots[:excess]:
                logger.info(f"Bot {bot.data.bot_number}: GREEN → RED")
                await bot.cancel_pending_order()
                bot.set_oracle_price(oracle_price)
                await bot.place_red_order()
                await asyncio.sleep(0.2)

    async def _load_bots(self) -> None:
        """Load bots from database."""
        existing_bots = await db.get_all_bots()

        if existing_bots:
            logger.info(f"Loading {len(existing_bots)} bots from database")
            for bot_data in existing_bots:
                bot = Bot(bot_data)
                self.bots.append(bot)
        else:
            logger.info("No existing bots, creating new ones")
            await self._create_bots()
            existing_bots = await db.get_all_bots()
            for bot_data in existing_bots:
                bot = Bot(bot_data)
                self.bots.append(bot)

    async def _initialize_bots_slowly(self) -> None:
        """Initialize bots with delays to avoid rate limiting."""
        logger.info("Initializing bots (13 sec delay for rate limit)...")

        for i, bot in enumerate(self.bots):
            try:
                success = await bot.initialize()
                if success:
                    logger.info(f"Bot {bot.data.bot_number} ready")
                else:
                    logger.warning(f"Bot {bot.data.bot_number} init failed")

                if i < len(self.bots) - 1:
                    await asyncio.sleep(13)

            except Exception as e:
                logger.error(f"Bot {bot.data.bot_number} init error: {e}")

        logger.info("All bots initialized")

    async def _create_bots(self) -> None:
        """Create new bots in the database."""
        async with db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, phone FROM users
                WHERE is_bot = TRUE
                ORDER BY phone
                LIMIT $1
            """,
                config.total_bots,
            )

        if len(rows) < config.total_bots:
            logger.error(f"Not enough bot users: {len(rows)} < {config.total_bots}")
            return

        async with db.acquire() as conn:
            for i, row in enumerate(rows):
                bot_number = i + 1
                level = ((i // 2) % config.levels) + 1
                initial_state = BotState.IDLE.value

                await conn.execute(
                    """
                    INSERT INTO bot_states (user_id, bot_number, level, state)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) DO UPDATE
                    SET level = $3, state = $4, updated_at = NOW()
                """,
                    row["id"],
                    bot_number,
                    level,
                    initial_state,
                )

                logger.info(f"Created bot {bot_number} (level {level})")

    async def _handle_place_order(self, bot_id: UUID, **params) -> dict:
        """Handle place order operation."""
        phone = params["phone"]
        side = params["side"]
        price = params["price"]
        quantity = params["quantity"]

        order_id = await api_client.place_order(phone, side, price, quantity)

        if order_id:
            async with db.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE limit_orders SET bot_id = $1 WHERE id = $2
                """,
                    bot_id,
                    order_id,
                )

            return {"success": True, "order_id": order_id}
        else:
            return {"success": False, "order_id": None}

    async def _handle_cancel_order(self, bot_id: UUID, **params) -> dict:
        """Handle cancel order operation."""
        phone = params["phone"]
        order_id = params["order_id"]

        success = await api_client.cancel_order(phone, order_id)
        return {"success": success}
