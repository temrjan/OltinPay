"""User deposit-intent schemas (demo fiat on-ramp)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DepositIntentRequest(BaseModel):
    """User's intent to fund their account with fiat UZS."""

    amount_uzs: int = Field(gt=0, lt=2**63)


class DepositRequisites(BaseModel):
    """Demo bank requisites the user pays to (settled by the bank connector)."""

    bank_name: str
    account_number: str
    mfo: str
    reference: str


class DepositIntentResponse(BaseModel):
    """Instructions returned for a deposit intent."""

    amount_uzs: int
    requisites: DepositRequisites
    note: str
