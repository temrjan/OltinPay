"""Auth API schemas."""

from pydantic import BaseModel, Field, field_validator


def normalize_phone(phone: str) -> str:
    """Normalize phone number - remove + and spaces."""
    return phone.replace("+", "").replace(" ", "").replace("-", "")


class RegisterRequest(BaseModel):
    """Registration request."""

    phone: str = Field(
        min_length=9,
        max_length=15,
        pattern=r"^\+?[0-9]+$",
        examples=["+998901234567"],
    )
    password: str = Field(min_length=6, max_length=100)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)


class LoginRequest(BaseModel):
    """Login request."""

    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Token response."""

    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TelegramAuthRequest(BaseModel):
    """Telegram Mini App authentication request."""

    init_data: str = Field(..., min_length=10, description="Telegram WebApp initData string")


class TelegramAuthResponse(BaseModel):
    """Telegram authentication response."""

    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool
    telegram_username: str | None = None
