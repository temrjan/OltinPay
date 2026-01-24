"""Telegram Mini App utilities."""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import TypedDict
from urllib.parse import parse_qs, unquote

import structlog

logger = structlog.get_logger()


class TelegramUserData(TypedDict):
    """Parsed Telegram user data."""

    telegram_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool
    photo_url: str | None


def validate_init_data(
    init_data: str, bot_token: str, max_age_seconds: int = 86400
) -> TelegramUserData | None:
    """
    Validate Telegram WebApp initData signature.

    Algorithm:
    1. Parse init_data as query string
    2. Sort params (except hash) alphabetically
    3. Create data_check_string with newline separator
    4. Compute HMAC-SHA256 with secret_key derived from bot_token
    5. Compare with received hash

    Args:
        init_data: Raw initData string from Telegram WebApp
        bot_token: Telegram bot token for signature verification
        max_age_seconds: Maximum age of auth_date (default 24 hours)

    Returns:
        TelegramUserData dict or None if invalid
    """
    try:
        # Parse query string
        parsed = parse_qs(init_data, keep_blank_values=True)

        # Extract hash
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            logger.warning("telegram_init_data_no_hash")
            return None

        # Build data_check_string (sorted, without hash)
        data_check_parts = []
        for key in sorted(parsed.keys()):
            if key != "hash":
                value = parsed[key][0]
                data_check_parts.append(f"{key}={value}")

        data_check_string = "\n".join(data_check_parts)

        # Compute secret_key = HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256,
        ).digest()

        # Compute hash = HMAC-SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison
        if not hmac.compare_digest(calculated_hash, received_hash):
            logger.warning("telegram_init_data_invalid_hash")
            return None

        # Verify auth_date freshness
        auth_date = int(parsed.get("auth_date", ["0"])[0])
        now = int(datetime.now(timezone.utc).timestamp())
        if now - auth_date > max_age_seconds:
            logger.warning("telegram_init_data_expired", age_seconds=now - auth_date)
            return None

        # Parse user data
        user_raw = parsed.get("user", ["{}"])[0]
        user_data = json.loads(unquote(user_raw))

        if not user_data.get("id"):
            logger.warning("telegram_init_data_no_user_id")
            return None

        return TelegramUserData(
            telegram_id=user_data["id"],
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            username=user_data.get("username"),
            language_code=user_data.get("language_code"),
            is_premium=user_data.get("is_premium", False),
            photo_url=user_data.get("photo_url"),
        )

    except Exception as e:
        logger.error("telegram_init_data_parse_error", error=str(e))
        return None
