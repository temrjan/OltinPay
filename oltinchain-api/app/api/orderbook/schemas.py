"""OrderBook API schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class PlaceOrderRequest(BaseModel):
    """Request to place a limit order."""
    
    side: str = Field(pattern="^(buy|sell)$", description="Order side: buy or sell")
    price: Decimal = Field(gt=0, le=1_000_000, description="Limit price in USD")
    quantity: Decimal = Field(gt=0, le=100_000, description="Amount of OLTIN")


class LimitOrderResponse(BaseModel):
    """Limit order response."""
    
    id: UUID
    user_id: UUID
    side: str
    price: Decimal
    quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
    filled_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)


class TradeResponse(BaseModel):
    """Trade response."""
    
    id: UUID
    buy_order_id: UUID
    sell_order_id: UUID
    price: Decimal
    quantity: Decimal
    taker_side: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PlaceOrderResponse(BaseModel):
    """Response after placing an order."""
    
    order: LimitOrderResponse
    trades: list[TradeResponse]
    message: str


class OrderBookLevel(BaseModel):
    """Single price level in order book."""
    
    price: str
    quantity: str


class OrderBookResponse(BaseModel):
    """Full order book response."""
    
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]


class UserOrdersResponse(BaseModel):
    """User's orders response."""
    
    orders: list[LimitOrderResponse]
    total: int


class RecentTradesResponse(BaseModel):
    """Recent trades response."""
    
    trades: list[TradeResponse]
