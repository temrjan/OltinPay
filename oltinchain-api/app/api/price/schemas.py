"""Price API schemas."""

from decimal import Decimal
from pydantic import BaseModel, Field


class GoldPriceResponse(BaseModel):
    """Current gold price response with buy/sell prices."""
    base_price: Decimal = Field(..., description="Market price per gram in UZS")
    buy_price: Decimal = Field(..., description="Ask price (user pays when buying)")
    sell_price: Decimal = Field(..., description="Bid price (user receives when selling)")
    spread_percent: float = Field(..., description="Spread percentage")
    currency: str = Field(default="UZS", description="Currency code")


class BuyQuoteRequest(BaseModel):
    """Request for buy quote."""
    amount_uzs: Decimal = Field(..., gt=0, description="Amount to spend in UZS")


class SellQuoteRequest(BaseModel):
    """Request for sell quote."""
    amount_oltin: Decimal = Field(..., gt=0, description="Amount of OLTIN to sell (grams)")


class QuoteResponse(BaseModel):
    """Quote response for buy/sell operations."""
    amount_uzs: Decimal = Field(..., description="Total UZS amount")
    amount_oltin: Decimal = Field(..., description="OLTIN amount (grams)")
    fee_uzs: Decimal = Field(..., description="Fee in UZS")
    gold_price_per_gram: Decimal = Field(..., description="Effective price per gram (with spread)")
    base_price_per_gram: Decimal = Field(..., description="Market price per gram")
    net_amount_uzs: Decimal = Field(..., description="Net UZS after fee")


class XauUsdPriceResponse(BaseModel):
    """Current XAU/USD price from replay strategy."""
    price_usd: float = Field(..., description="Gold price in USD per ounce")
    price_change_pct: float = Field(..., description="Price change percentage")
    data_index: int = Field(..., description="Current index in historical data")
    data_date: str = Field(..., description="Date from historical data")
    timestamp: str = Field(..., description="Timestamp of last update")


class XauUsdHistoryItem(BaseModel):
    """Single price point in history."""
    timestamp: str
    price_usd: float
    change_pct: float


class XauUsdHistoryResponse(BaseModel):
    """XAU/USD price history for charting."""
    prices: list[dict] = Field(default_factory=list, description="Price history points")
    count: int = Field(..., description="Number of points returned")
