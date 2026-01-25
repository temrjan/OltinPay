"""Auth utilities for Telegram and JWT."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, unquote

from jose import jwt
from pydantic import BaseModel

from src.config import settings


class TelegramUser(BaseModel):
    """Parsed Telegram user data."""

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None


def validate_telegram_init_data(init_data: str) -> TelegramUser | None:
    """Validate Telegram WebApp initData and extract user.

    Args:
        init_data: Raw initData string from Telegram WebApp.

    Returns:
        TelegramUser if valid, None otherwise.
    """
    try:
        parsed = parse_qs(init_data)

        # Get hash
        received_hash = parsed.get("hash", [""])[0]
        if not received_hash:
            return None

        # Build data check string (sorted, excluding hash)
        data_check_parts = []
        for key in sorted(parsed.keys()):
            if key != "hash":
                value = parsed[key][0]
                data_check_parts.append(f"{key}={value}")

        data_check_string = "\n".join(data_check_parts)

        # Calculate secret key
        if not settings.telegram_bot_token:
            return None
        bot_token = settings.telegram_bot_token.get_secret_value()
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256,
        ).digest()

        # Calculate expected hash
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Validate hash
        if not hmac.compare_digest(received_hash, expected_hash):
            return None

        # Check auth_date (valid for 24 hours)
        auth_date = int(parsed.get("auth_date", ["0"])[0])
        if datetime.now(UTC).timestamp() - auth_date > 86400:
            return None

        # Parse user data
        user_data = parsed.get("user", [""])[0]
        if not user_data:
            return None

        user_json = json.loads(unquote(user_data))
        return TelegramUser(**user_json)

    except Exception:
        return None


def create_access_token(user_id: str) -> str:
    """Create JWT access token.

    Args:
        user_id: User's UUID as string.

    Returns:
        Encoded JWT token.
    """
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
