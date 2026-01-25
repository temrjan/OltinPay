"""Balance Pydantic schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field


class AccountBalance(BaseModel):
    """Single account balance."""

    usd: Decimal
    oltin: Decimal


class BalancesResponse(BaseModel):
    """All user balances response."""

    total_usd: Decimal
    wallet: AccountBalance
    exchange: AccountBalance
    staking: AccountBalance


class InternalTransferRequest(BaseModel):
    """Internal transfer request (between own accounts)."""

    from_account: str = Field(..., pattern="^(wallet|exchange|staking)$")
    to_account: str = Field(..., pattern="^(wallet|exchange|staking)$")
    currency: str = Field(..., pattern="^(USD|OLTIN)$")
    amount: Decimal = Field(..., gt=0)


class InternalTransferResponse(BaseModel):
    """Internal transfer response."""

    success: bool = True
    from_account: str
    to_account: str
    currency: str
    amount: Decimal
