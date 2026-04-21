"""User Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OltinIdCreate(BaseModel):
    """Schema for creating oltin_id."""

    oltin_id: str = Field(..., min_length=3, max_length=30)

    @field_validator("oltin_id")
    @classmethod
    def validate_oltin_id(cls, v: str) -> str:
        """Validate oltin_id format: lowercase letters, numbers, underscores."""
        v = v.lower().strip()
        if v.startswith("@"):
            v = v[1:]
        if not v.replace("_", "").isalnum():
            raise ValueError(
                "oltin_id must contain only letters, numbers, and underscores"
            )
        if v[0].isdigit():
            raise ValueError("oltin_id cannot start with a number")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user."""

    language: str | None = Field(None, pattern="^(uz|ru|en)$")


class WalletRegister(BaseModel):
    """Register a non-custodial wallet address for the current user.

    Called by the Mini App after the client-side onboarding wizard
    generates a BIP39 seed and derives the EVM address.
    """

    wallet_address: str = Field(..., pattern="^0x[a-fA-F0-9]{40}$")


class UserResponse(BaseModel):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telegram_id: int
    oltin_id: str
    language: str
    wallet_address: str | None = None
    created_at: datetime


class UserSearchResult(BaseModel):
    """User search result."""

    model_config = ConfigDict(from_attributes=True)

    oltin_id: str
    telegram_id: int
