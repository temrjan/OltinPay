"""Price API schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PriceResponse(BaseModel):
    """Current price response."""
    
    price: Decimal = Field(description="Current OLTIN price in USD")
    bid: Decimal = Field(description="Bid price (sell price for users)")
    ask: Decimal = Field(description="Ask price (buy price for users)")
    spread_percent: Decimal = Field(description="Current spread percentage")
    timestamp: datetime = Field(description="Price timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class CycleStateResponse(BaseModel):
    """Current market cycle state."""
    
    cycle_number: int = Field(ge=1, description="Current cycle number")
    phase: str = Field(description="Current Wyckoff phase")
    day_in_cycle: float = Field(ge=0, le=7, description="Day position in cycle")
    cycle_progress: float = Field(ge=0, le=1, description="Progress 0-1")
    
    start_price: Decimal = Field(description="Cycle start price")
    current_price: Decimal = Field(description="Current target price")
    peak_price: Decimal = Field(description="Expected cycle peak")
    bottom_price: Decimal = Field(description="Expected cycle bottom")
    end_price: Decimal = Field(description="Expected cycle end price")
    
    total_growth_percent: Decimal = Field(description="Growth from cycle start")
    
    model_config = ConfigDict(from_attributes=True)


class PriceHistoryItem(BaseModel):
    """Single price history point."""
    
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Field(default=Decimal("0"))
    
    model_config = ConfigDict(from_attributes=True)


class PriceHistoryResponse(BaseModel):
    """Price history (OHLCV) response."""
    
    interval: str = Field(description="Candle interval (1m, 5m, 1h, 1d)")
    data: list[PriceHistoryItem]
    
    model_config = ConfigDict(from_attributes=True)
