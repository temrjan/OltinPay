"""Authentication service."""

import structlog

from app.application.interfaces.user_repository import UserRepositoryProtocol
from app.domain.exceptions import AuthenticationError, UserAlreadyExistsError
from app.infrastructure.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

logger = structlog.get_logger()


class AuthService:
    """Service for authentication operations."""

    def __init__(self, user_repo: UserRepositoryProtocol):
        self.user_repo = user_repo

    async def register(self, phone: str, password: str) -> dict:
        """Register a new user.

        Args:
            phone: User phone number
            password: User password

        Returns:
            Dict with user_id and tokens

        Raises:
            UserAlreadyExistsError: If phone already registered
        """
        existing = await self.user_repo.get_by_phone(phone)
        if existing:
            raise UserAlreadyExistsError(f"Phone {phone} already registered")

        user = await self.user_repo.create(
            phone=phone,
            password_hash=hash_password(password),
        )

        logger.info("user_registered", user_id=str(user.id), phone=phone)

        return {
            "user_id": str(user.id),
            "access_token": create_access_token(str(user.id)),
            "refresh_token": create_refresh_token(str(user.id)),
        }

    async def login(self, phone: str, password: str) -> dict:
        """Authenticate a user.

        Args:
            phone: User phone number
            password: User password

        Returns:
            Dict with user_id and tokens

        Raises:
            AuthenticationError: If credentials are invalid
        """
        user = await self.user_repo.get_by_phone(phone)
        if not user or not verify_password(password, user.password_hash):
            logger.warning("login_failed", phone=phone)
            raise AuthenticationError("Invalid credentials")

        logger.info("user_logged_in", user_id=str(user.id))

        return {
            "user_id": str(user.id),
            "access_token": create_access_token(str(user.id)),
            "refresh_token": create_refresh_token(str(user.id)),
        }

    async def refresh_tokens(self, user_id: str) -> dict:
        """Refresh access token.

        Args:
            user_id: User ID from refresh token

        Returns:
            Dict with new tokens
        """
        return {
            "user_id": user_id,
            "access_token": create_access_token(user_id),
            "refresh_token": create_refresh_token(user_id),
        }

    async def telegram_auth(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        photo_url: str | None,
    ) -> dict:
        """Authenticate user via Telegram Mini App.

        Creates a new user if telegram_id not found,
        otherwise updates Telegram data and returns tokens.

        Args:
            telegram_id: Telegram user ID
            username: Telegram @username
            first_name: User's first name
            photo_url: Profile photo URL

        Returns:
            Dict with user_id, tokens, and is_new_user flag
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        is_new_user = False

        if not user:
            # Create new user
            user = await self.user_repo.create_from_telegram(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                photo_url=photo_url,
            )
            is_new_user = True
            logger.info(
                "telegram_user_registered",
                user_id=str(user.id),
                telegram_id=telegram_id,
            )
        else:
            # Update Telegram data if changed
            user = await self.user_repo.update_telegram_data(
                user=user,
                username=username,
                first_name=first_name,
                photo_url=photo_url,
            )
            logger.info(
                "telegram_user_logged_in",
                user_id=str(user.id),
                telegram_id=telegram_id,
            )

        return {
            "user_id": str(user.id),
            "access_token": create_access_token(str(user.id)),
            "refresh_token": create_refresh_token(str(user.id)),
            "is_new_user": is_new_user,
            "telegram_username": user.telegram_username,
        }
