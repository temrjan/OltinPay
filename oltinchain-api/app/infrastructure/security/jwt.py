"""JWT token utilities."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import settings
from app.domain.exceptions import AuthenticationError


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Create an access token for a user."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )


def create_refresh_token(user_id: str) -> str:
    """Create a refresh token for a user."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=["HS256"],
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}") from e
