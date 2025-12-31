"""Bot orchestrator - manages all trading bots."""

import asyncio
import logging
from decimal import Decimal

from bots import MarketMakerBot, ArbitrageurBot, MomentumBot, WhaleBot, BaseBot
from clients.api_client import APIClient
from clients.oracle_client import OracleClient
from config import config

logger = logging.getLogger(__name__)


def generate_phone(prefix: str, index: int) -> str:
    """Generate phone number for bot."""
    prefixes = {
        "mm": 900,
        "arb": 901,
        "mom": 902,
        "whale": 903,
    }
    p = prefixes.get(prefix, 999)
    return f"+998{p}{index:06d}"


class BotOrchestrator:
    """Manages all trading bots."""

    def __init__(self):
        self.api_client = APIClient()
        self.oracle_client = OracleClient()
        self.bots: list[BaseBot] = []
        self.running = False

    async def initialize(self):
        """Initialize all bots (login only, users already in DB)."""
        logger.info("Initializing bots...")

        # Create Market Makers (40%)
        for i in range(config.market_maker_count):
            phone = generate_phone("mm", i)
            await self._login_bot(phone)

            bot = MarketMakerBot(
                bot_id=phone,
                api_client=self.api_client,
                initial_usd=config.mm_initial_usd,
                initial_oltin=config.mm_initial_oltin,
            )
            self.bots.append(bot)

        # Create Arbitrageurs (30%)
        for i in range(config.arbitrageur_count):
            phone = generate_phone("arb", i)
            await self._login_bot(phone)

            bot = ArbitrageurBot(
                bot_id=phone,
                api_client=self.api_client,
                initial_usd=config.arb_initial_usd,
                initial_oltin=config.arb_initial_oltin,
            )
            self.bots.append(bot)

        # Create Momentum bots (20%)
        for i in range(config.momentum_count):
            phone = generate_phone("mom", i)
            await self._login_bot(phone)

            bot = MomentumBot(
                bot_id=phone,
                api_client=self.api_client,
                initial_usd=config.momentum_initial_usd,
                initial_oltin=config.momentum_initial_oltin,
            )
            self.bots.append(bot)

        # Create Whale bots (10%)
        for i in range(config.whale_count):
            phone = generate_phone("whale", i)
            await self._login_bot(phone)

            bot = WhaleBot(
                bot_id=phone,
                api_client=self.api_client,
                initial_usd=config.whale_initial_usd,
                initial_oltin=config.whale_initial_oltin,
            )
            self.bots.append(bot)

        logger.info(f"Initialized {len(self.bots)} bots")

    async def _login_bot(self, phone: str) -> bool:
        """Login a bot."""
        try:
            await self.api_client.login(phone, config.bot_password)
            logger.info(f"Logged in bot: {phone}")
            return True
        except Exception as e:
            logger.error(f"Failed to login bot {phone}: {e}")
            return False

    async def run(self):
        """Main bot loop."""
        self.running = True
        logger.info("Starting bot orchestrator...")

        await self.initialize()

        cycle = 0
        while self.running:
            try:
                cycle += 1
                logger.info(f"=== Cycle {cycle} ===")

                # Get market state
                oracle_price = await self.oracle_client.get_price()
                cycle_state = await self.oracle_client.get_cycle_state()
                market_price = await self.oracle_client.get_market_price()

                logger.info(
                    f"Oracle: ${oracle_price}, Market: ${market_price}, "
                    f"Phase: {cycle_state.phase}"
                )

                # Run all bots in batches
                batch_size = 10
                for i in range(0, len(self.bots), batch_size):
                    batch = self.bots[i:i+batch_size]
                    tasks = [
                        bot.tick(oracle_price, market_price, cycle_state)
                        for bot in batch
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await asyncio.sleep(1)

                # Wait for next cycle
                await asyncio.sleep(config.cycle_interval)

            except asyncio.CancelledError:
                logger.info("Orchestrator cancelled")
                break
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        """Stop the orchestrator."""
        logger.info("Stopping orchestrator...")
        self.running = False
        await self.api_client.close()
        await self.oracle_client.close()

    def get_stats(self) -> dict:
        """Get bot statistics."""
        stats = {
            "total_bots": len(self.bots),
            "by_type": {},
        }

        for bot in self.bots:
            bot_type = bot.bot_type
            if bot_type not in stats["by_type"]:
                stats["by_type"][bot_type] = {
                    "count": 0,
                    "total_usd": Decimal("0"),
                    "total_oltin": Decimal("0"),
                    "orders_placed": 0,
                }

            stats["by_type"][bot_type]["count"] += 1
            stats["by_type"][bot_type]["total_usd"] += bot.balance_usd
            stats["by_type"][bot_type]["total_oltin"] += bot.balance_oltin
            stats["by_type"][bot_type]["orders_placed"] += bot.state.orders_placed

        return stats
