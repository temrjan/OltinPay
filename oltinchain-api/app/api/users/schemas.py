"""Users API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User profile response."""

    id: str
    phone: str
    wallet_address: str | None
    kyc_level: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateUserRequest(BaseModel):
    """Update user request."""

    wallet_address: str | None = Field(
        default=None,
        min_length=42,
        max_length=42,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        examples=["0x742d35Cc6634C0532925a3b844Bc9e7595f1B7aE"],
    )


class UserBalanceResponse(BaseModel):
    """User balance response."""

    asset: str
    available: str
    locked: str


class UserWithBalancesResponse(UserResponse):
    """User with balances."""

    balances: list[UserBalanceResponse] = []
