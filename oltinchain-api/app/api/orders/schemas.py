"""Orders API schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class BuyOrderRequest(BaseModel):
    """Request for buying OLTIN with USD."""
    
    amount_usd: Decimal = Field(
        ...,
        gt=0,
        le=1_000_000,
        description="Amount of USD to spend",
    )


class SellOrderRequest(BaseModel):
    """Request for selling OLTIN for USD."""
    
    amount_oltin: Decimal = Field(
        ...,
        gt=0,
        le=100_000,
        description="Amount of OLTIN to sell (grams)",
    )


class OrderResponse(BaseModel):
    """Order response."""
    
    id: UUID
    type: str = Field(description="Order type: buy or sell")
    status: str = Field(description="Order status: pending, completed, failed")
    amount_usd: Decimal = Field(alias="amount_uzs")
    amount_oltin: Decimal
    price_per_gram: Decimal
    fee_usd: Decimal = Field(alias="fee_uzs")
    tx_hash: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class OrderListResponse(BaseModel):
    """List of orders."""
    
    orders: list[OrderResponse]
    total: int
