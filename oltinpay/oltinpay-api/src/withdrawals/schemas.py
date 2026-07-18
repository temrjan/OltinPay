"""Withdrawal schemas (user-facing, snake_case like the rest of the user API)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — runtime type for Pydantic field
from uuid import UUID  # noqa: TC003 — runtime type for Pydantic field

from pydantic import BaseModel, ConfigDict, Field


class WithdrawalCreateRequest(BaseModel):
    """User request to withdraw UZD to fiat."""

    amount_uzd: int = Field(gt=0, lt=2**63)


class WithdrawalResponse(BaseModel):
    """A withdrawal as seen by its owner."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount_uzd: int
    amount_wei: str
    status: str
    tx_hash: str | None = None
    created_at: datetime
    confirmed_at: datetime | None = None
