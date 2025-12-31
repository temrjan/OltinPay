"""Configuration for Trading Bots v3."""

import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Config:
    """Bot system configuration."""

    # API endpoints
    api_base_url: str = os.getenv("API_BASE_URL", "http://oltinchain-api:8000")

    # Bot counts (50 total)
    market_maker_count: int = 20  # 40%
    arbitrageur_count: int = 15   # 30%
    momentum_count: int = 10      # 20%
    whale_count: int = 5          # 10%

    # Initial balances
    mm_initial_usd: Decimal = Decimal("5000")
    mm_initial_oltin: Decimal = Decimal("10")

    arb_initial_usd: Decimal = Decimal("3000")
    arb_initial_oltin: Decimal = Decimal("8")

    momentum_initial_usd: Decimal = Decimal("2000")
    momentum_initial_oltin: Decimal = Decimal("5")

    whale_initial_usd: Decimal = Decimal("10000")
    whale_initial_oltin: Decimal = Decimal("25")

    # Trading parameters
    cycle_interval: int = int(os.getenv("CYCLE_INTERVAL", "45"))  # seconds
    order_ttl: int = int(os.getenv("ORDER_TTL", "300"))  # 5 minutes

    # Bot password (same for all bots)
    bot_password: str = os.getenv("BOT_PASSWORD", "bot123")


config = Config()
