"""Welcome bonus schemas."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003  — required at runtime for Pydantic field

from pydantic import BaseModel, ConfigDict


class WelcomeClaimResponse(BaseModel):
    """Response after claiming the welcome bonus."""

    model_config = ConfigDict(from_attributes=True)

    tx_hash: str
    amount_wei: str
    wallet_address: str
    claimed_at: datetime


class WelcomeStatusResponse(BaseModel):
    """Whether the user has already claimed the welcome bonus."""

    claimed: bool
    tx_hash: str | None = None
    claimed_at: datetime | None = None
