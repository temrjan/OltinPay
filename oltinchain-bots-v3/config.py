"""Configuration for OltinChain Market Making Bots."""

import os
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class BotConfig:
    """Bot system configuration."""

    # API
    api_base_url: str = os.getenv("API_BASE_URL", "http://oltinchain-api:8000")
    bot_password: str = os.getenv("BOT_PASSWORD", "bot123")

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/oltinchain"
    )

    # Bot distribution
    total_bots: int = 20
    levels: int = 10
    bots_per_level: int = 2  # 1 Ask + 1 Bid initially

    # Pricing (relative to oracle price)
    base_spread_pct: Decimal = Decimal("0.003")  # 0.3%
    level_step_pct: Decimal = Decimal("0.002")  # 0.2% per level

    # Order sizes per level (USD)
    order_sizes: dict = field(
        default_factory=lambda: {
            1: Decimal("50"),
            2: Decimal("75"),
            3: Decimal("100"),
            4: Decimal("150"),
            5: Decimal("200"),
            6: Decimal("300"),
            7: Decimal("400"),
            8: Decimal("500"),
            9: Decimal("750"),
            10: Decimal("1000"),
        }
    )

    # Initial capital per bot
    initial_usd_per_bot: Decimal = Decimal("1000")
    initial_oltin_per_bot: Decimal = Decimal("4")  # ~$1000 at $250/OLTIN

    # Rebalancing thresholds
    soft_threshold: Decimal = Decimal("0.20")  # 20%
    hard_threshold: Decimal = Decimal("0.40")  # 40%
    critical_threshold: Decimal = Decimal("0.60")  # 60%
    hard_correction_pct: Decimal = Decimal("0.25")
    critical_correction_pct: Decimal = Decimal("0.50")
    rebalance_cooldown_sec: int = 300  # 5 minutes
    max_rebalances_per_minute: int = 3

    # System-wide side balancing (RED/GREEN ratio)
    system_balance_min: Decimal = Decimal("0.40")  # 40% minimum on one side
    system_balance_max: Decimal = Decimal("0.60")  # 60% maximum on one side
    system_rebalance_cooldown_sec: int = 30

    # Queue processing
    queue_delay_ms: int = 100  # 100ms between operations

    # Oracle
    oracle_cache_ttl_sec: int = 5
    max_price_deviation_pct: Decimal = Decimal("0.10")  # 10%

    # Cycle timing
    health_check_interval_sec: int = 30
    order_check_interval_sec: int = 5


config = BotConfig()
