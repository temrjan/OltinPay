"""Auth API schemas."""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Registration request."""

    phone: str = Field(
        min_length=9,
        max_length=15,
        pattern=r"^\+?[0-9]+$",
        examples=["+998901234567"],
    )
    password: str = Field(min_length=6, max_length=100)


class LoginRequest(BaseModel):
    """Login request."""

    phone: str
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Token response."""

    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
