"""Transfer Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransferRequest(BaseModel):
    """Transfer request."""

    to_oltin_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)


class TransferResponse(BaseModel):
    """Transfer response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    fee: Decimal
    net_amount: Decimal  # amount - fee (what receiver gets)
    status: str
    created_at: datetime


class TransferDetailResponse(BaseModel):
    """Detailed transfer response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_oltin_id: str
    to_oltin_id: str
    amount: Decimal
    fee: Decimal
    tx_hash: str | None
    status: str
    created_at: datetime
    confirmed_at: datetime | None


class TransferListResponse(BaseModel):
    """Transfer list item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    direction: str  # 'sent' or 'received'
    counterparty: str  # oltin_id of the other party
    amount: Decimal
    fee: Decimal
    status: str
    created_at: datetime
