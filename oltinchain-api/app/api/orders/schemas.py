"""Orders API schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BuyOrderRequest(BaseModel):
    """Request for buying OLTIN with UZS."""
    amount_uzs: Decimal = Field(..., gt=0, description="Amount of UZS to spend")


class SellOrderRequest(BaseModel):
    """Request for selling OLTIN for UZS."""
    amount_oltin: Decimal = Field(..., gt=0, description="Amount of OLTIN to sell (grams)")


class OrderResponse(BaseModel):
    """Order response."""
    id: UUID
    type: str = Field(..., description="Order type: buy or sell")
    status: str = Field(..., description="Order status: pending, completed, failed")
    amount_uzs: Decimal
    amount_oltin: Decimal
    price_per_gram: Decimal
    fee_uzs: Decimal
    tx_hash: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """List of orders."""
    orders: list[OrderResponse]
    total: int
