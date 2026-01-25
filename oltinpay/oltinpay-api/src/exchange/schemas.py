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


# ===== SWAP SCHEMAS =====


class SwapRequest(BaseModel):
    """Swap request - instant exchange USD <-> OLTIN."""

    side: str = Field(
        ..., pattern="^(buy|sell)$", description="buy = USD->OLTIN, sell = OLTIN->USD"
    )
    amount: Decimal = Field(..., gt=0, description="Amount to swap")
    amount_type: str = Field(
        "from",
        pattern="^(from|to)$",
        description="Is amount what you give (from) or receive (to)",
    )


class SwapQuoteResponse(BaseModel):
    """Swap quote - preview before execution."""

    side: str
    from_currency: str
    from_amount: Decimal
    to_currency: str
    to_amount: Decimal
    price: Decimal  # Price per OLTIN
    fee: Decimal
    fee_percent: Decimal


class SwapResponse(BaseModel):
    """Swap execution response."""

    success: bool = True
    side: str
    from_currency: str
    from_amount: Decimal
    to_currency: str
    to_amount: Decimal
    price: Decimal
    fee: Decimal
