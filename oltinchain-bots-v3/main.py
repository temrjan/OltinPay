"""Main entry point for Trading Bots v3."""

import asyncio
import logging
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


async def main():
    """Main async entry point."""
    logger.info("=" * 60)
    logger.info("OltinChain Trading Bots v3")
    logger.info("=" * 60)

    # Initialize bots in database
    logger.info("Initializing bots in database...")
    from init_bots import init_bots
    try:
        await init_bots()
    except Exception as e:
        logger.error(f"Failed to init bots: {e}")
        # Continue anyway, bots might already exist

    # Start orchestrator
    from services.orchestrator import BotOrchestrator
    orchestrator = BotOrchestrator()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(orchestrator.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        await orchestrator.stop()

    logger.info("Bots stopped")


if __name__ == "__main__":
    asyncio.run(main())
