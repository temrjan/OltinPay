"""Staking Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class StakingInfoResponse(BaseModel):
    """Staking info response."""

    balance: Decimal
    locked_until: datetime | None
    is_locked: bool
    apy: Decimal
    daily_reward: Decimal
    total_earned: Decimal


class StakingDepositRequest(BaseModel):
    """Staking deposit request."""

    amount: Decimal = Field(..., gt=0)


class StakingDepositResponse(BaseModel):
    """Staking deposit response."""

    new_balance: Decimal
    locked_until: datetime


class StakingWithdrawRequest(BaseModel):
    """Staking withdraw request."""

    amount: Decimal = Field(..., gt=0)


class StakingWithdrawResponse(BaseModel):
    """Staking withdraw response."""

    withdrawn: Decimal
    remaining: Decimal


class StakingRewardResponse(BaseModel):
    """Staking reward item."""

    date: date
    amount: Decimal
    balance_snapshot: Decimal
