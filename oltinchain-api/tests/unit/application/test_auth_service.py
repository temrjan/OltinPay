"""Unit tests for auth service."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.services.auth_service import AuthService
from app.domain.exceptions import AuthenticationError, UserAlreadyExistsError


@pytest.fixture
def mock_user_repo():
    """Create mock user repository."""
    return AsyncMock()


@pytest.fixture
def auth_service(mock_user_repo):
    """Create auth service with mock repo."""
    return AuthService(mock_user_repo)


class TestRegister:
    """Tests for register method."""

    async def test_register_new_user_succeeds(self, auth_service, mock_user_repo):
        # Arrange
        mock_user_repo.get_by_phone.return_value = None
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user_repo.create.return_value = mock_user

        # Act
        result = await auth_service.register("+998901234567", "password123")

        # Assert
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user_id"] == str(mock_user.id)
        mock_user_repo.create.assert_called_once()

    async def test_register_existing_phone_fails(self, auth_service, mock_user_repo):
        # Arrange
        mock_user_repo.get_by_phone.return_value = MagicMock()

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register("+998901234567", "password123")


class TestLogin:
    """Tests for login method."""

    async def test_login_valid_credentials_succeeds(self, auth_service, mock_user_repo):
        # Arrange
        mock_user = MagicMock()
        mock_user.id = uuid4()
        # Password hash for "password123"
        from app.infrastructure.security import hash_password
        mock_user.password_hash = hash_password("password123")
        mock_user_repo.get_by_phone.return_value = mock_user

        # Act
        result = await auth_service.login("+998901234567", "password123")

        # Assert
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user_id"] == str(mock_user.id)

    async def test_login_wrong_password_fails(self, auth_service, mock_user_repo):
        # Arrange
        mock_user = MagicMock()
        from app.infrastructure.security import hash_password
        mock_user.password_hash = hash_password("password123")
        mock_user_repo.get_by_phone.return_value = mock_user

        # Act & Assert
        with pytest.raises(AuthenticationError):
            await auth_service.login("+998901234567", "wrongpassword")

    async def test_login_user_not_found_fails(self, auth_service, mock_user_repo):
        # Arrange
        mock_user_repo.get_by_phone.return_value = None

        # Act & Assert
        with pytest.raises(AuthenticationError):
            await auth_service.login("+998901234567", "password123")
