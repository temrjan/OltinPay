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


class BuyQuoteRequest(BaseModel):
    """Request for buy quote."""

    amount_usd: Decimal = Field(gt=0, description="Amount in USD to spend")


class SellQuoteRequest(BaseModel):
    """Request for sell quote."""

    amount_oltin: Decimal = Field(gt=0, description="Amount of OLTIN to sell")


class QuoteResponse(BaseModel):
    """Quote response."""

    amount_usd: Decimal
    amount_oltin: Decimal
    fee_usd: Decimal
    price_per_gram: Decimal

    model_config = ConfigDict(from_attributes=True)
