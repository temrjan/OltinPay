"""Main entry point for OltinChain Market Making Bots."""

import asyncio
import logging
import signal
import sys

from orchestrator import Orchestrator
from active_orchestrator import ActiveOrchestrator
from database import db  # Use global instance
from oracle import oracle  # Use global instance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Reduce noise from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main async entry point."""
    # Initialize Market Maker orchestrator (this also connects to DB)
    market_maker_orchestrator = Orchestrator()

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    active_orchestrator = None

    def shutdown_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(market_maker_orchestrator.stop())
        if active_orchestrator:
            asyncio.create_task(active_orchestrator.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    try:
        # Start Market Maker orchestrator (connects DB, loads bots)
        await market_maker_orchestrator.start()

        # Initialize Active orchestrator with shared resources
        # Active Traders are created via SQL migration (003_create_active_traders.sql)
        active_orchestrator = ActiveOrchestrator(db=db, oracle=oracle)

        # Set delay for Active Traders (wait for Market Maker logins to complete)
        # 20 bots * 13 sec = 260 sec = ~5 minutes
        active_orchestrator.startup_delay = 300

        # Run both orchestrators concurrently
        await asyncio.gather(
            market_maker_orchestrator.run(),
            active_orchestrator.run(),
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await market_maker_orchestrator.stop()
        if active_orchestrator:
            await active_orchestrator.stop()

    logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
