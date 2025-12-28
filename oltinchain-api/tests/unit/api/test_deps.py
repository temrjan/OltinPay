"""Unit tests for API dependencies."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user, get_current_user_id
from app.infrastructure.security import create_access_token, create_refresh_token


class TestGetCurrentUserId:
    """Tests for get_current_user_id."""

    async def test_valid_token_returns_user_id(self):
        # Arrange
        user_id = str(uuid4())
        token = create_access_token(user_id)
        authorization = f"Bearer {token}"

        # Act
        result = await get_current_user_id(authorization)

        # Assert
        assert str(result) == user_id

    async def test_missing_header_raises_401(self):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(None)
        assert exc_info.value.status_code == 401

    async def test_invalid_format_raises_401(self):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id("InvalidToken")
        assert exc_info.value.status_code == 401

    async def test_invalid_token_raises_401(self):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id("Bearer invalid-token")
        assert exc_info.value.status_code == 401

    async def test_refresh_token_raises_401(self):
        # Arrange - using refresh token instead of access token
        user_id = str(uuid4())
        token = create_refresh_token(user_id)
        authorization = f"Bearer {token}"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(authorization)
        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail


class TestGetCurrentUser:
    """Tests for get_current_user."""

    async def test_valid_user_returns_user(self):
        # Arrange
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True

        mock_session = AsyncMock()

        # Mock the repository
        with pytest.MonkeyPatch().context() as m:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user

            # Act
            from app.infrastructure.repositories.user_repo import UserRepository
            original_init = UserRepository.__init__

            def mock_init(self, session):
                self.session = session
                self.get_by_id = mock_repo.get_by_id

            m.setattr(UserRepository, "__init__", mock_init)

            result = await get_current_user(user_id, mock_session)

            # Assert
            assert result == mock_user

    async def test_user_not_found_raises_401(self):
        # Arrange
        user_id = uuid4()
        mock_session = AsyncMock()

        with pytest.MonkeyPatch().context() as m:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None

            from app.infrastructure.repositories.user_repo import UserRepository

            def mock_init(self, session):
                self.session = session
                self.get_by_id = mock_repo.get_by_id

            m.setattr(UserRepository, "__init__", mock_init)

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(user_id, mock_session)
            assert exc_info.value.status_code == 401

    async def test_inactive_user_raises_403(self):
        # Arrange
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = False

        mock_session = AsyncMock()

        with pytest.MonkeyPatch().context() as m:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user

            from app.infrastructure.repositories.user_repo import UserRepository

            def mock_init(self, session):
                self.session = session
                self.get_by_id = mock_repo.get_by_id

            m.setattr(UserRepository, "__init__", mock_init)

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(user_id, mock_session)
            assert exc_info.value.status_code == 403
