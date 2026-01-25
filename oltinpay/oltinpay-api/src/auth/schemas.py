"""Auth Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel

from src.users.schemas import UserResponse


class TelegramAuthRequest(BaseModel):
    """Telegram authentication request."""

    init_data: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Authentication response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new: bool


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id as string
    exp: datetime
    type: str = "access"
