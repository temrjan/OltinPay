"""Exchange Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderBookLevel(BaseModel):
    """Orderbook price level."""

    price: Decimal
    quantity: Decimal


class OrderBookResponse(BaseModel):
    """Orderbook response."""

    bids: list[OrderBookLevel]  # Buy orders (highest first)
    asks: list[OrderBookLevel]  # Sell orders (lowest first)
    mid_price: Decimal


class PriceResponse(BaseModel):
    """Current price response."""

    bid: Decimal
    ask: Decimal
    mid: Decimal


class OrderRequest(BaseModel):
    """Create order request."""

    side: str = Field(..., pattern="^(buy|sell)$")
    type: str = Field("limit", pattern="^(market|limit)$")
    price: Decimal | None = Field(None, gt=0)
    quantity: Decimal = Field(..., gt=0)


class OrderResponse(BaseModel):
    """Order response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    side: str
    order_type: str
    price: Decimal | None
    quantity: Decimal
    filled_quantity: Decimal
    status: str
    created_at: datetime


class TradeResponse(BaseModel):
    """Trade response."""

    model_config = ConfigDict(from_attributes=True)

    price: Decimal
    quantity: Decimal
    side: str  # 'buy' if buyer initiated, 'sell' if seller initiated
    created_at: datetime
