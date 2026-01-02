"""Data models for the bot system.

Terminology:
- RED = Ask/Sell side (продажа)
- GREEN = Bid/Buy side (покупка)
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID


class BotState(Enum):
    """
    Possible states for a market making bot.

    State Machine:
    IDLE → RED/GREEN → RED_DONE/GREEN_DONE → GREEN/RED → (cycle)

    Terminology:
    - RED states = Sell/Ask side
    - GREEN states = Buy/Bid side
    """

    IDLE = "idle"

    # Active states (has pending order)
    RED = "white_ask"  # Has pending SELL order (Ask), waiting for fill
    GREEN = "white_bid"  # Has pending BUY order (Bid), waiting for fill

    # Transition states (order filled, placing new order)
    RED_DONE = "green_ask"  # SELL filled → placing BUY
    GREEN_DONE = "green_bid"  # BUY filled → placing SELL

    REBALANCING = "rebalancing"
    ERROR = "error"

    # Aliases for backwards compatibility
    WHITE_ASK = "white_ask"
    WHITE_BID = "white_bid"
    GREEN_ASK = "green_ask"
    GREEN_BID = "green_bid"


class OrderSide(Enum):
    """Order side."""

    BUY = "buy"  # GREEN
    SELL = "sell"  # RED


@dataclass
class BotData:
    """Bot state data from database."""

    id: UUID
    user_id: UUID
    bot_number: int
    level: int
    state: BotState
    pending_order_id: Optional[UUID]
    total_trades: int
    last_trade_at: Optional[datetime]
    state_changed_at: datetime
    created_at: datetime
    updated_at: datetime

    # Balances (loaded separately)
    usd_balance: Decimal = Decimal("0")
    oltin_balance: Decimal = Decimal("0")

    # Runtime state
    phone: str = ""
    access_token: str = ""

    @property
    def is_red(self) -> bool:
        """Is bot on RED (sell) side?"""
        return self.state in [BotState.RED, BotState.GREEN_DONE]

    @property
    def is_green(self) -> bool:
        """Is bot on GREEN (buy) side?"""
        return self.state in [BotState.GREEN, BotState.RED_DONE]


@dataclass
class OrderData:
    """Order data."""

    id: UUID
    user_id: UUID
    side: str
    price: Decimal
    quantity: Decimal
    filled_quantity: Decimal
    status: str
    created_at: datetime
    bot_id: Optional[UUID] = None


@dataclass
class OrderOperation:
    """Operation to be queued."""

    id: UUID
    op_type: str  # "place", "cancel", "market_buy", "market_sell"
    bot_id: UUID
    params: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class OraclePrice:
    """Oracle price data."""

    price: Decimal
    source: str
    timestamp: datetime


@dataclass
class LevelPrice:
    """Calculated price for a level."""

    level: int
    side: OrderSide
    price: Decimal
    spread_pct: Decimal
