"""Unit tests for security module."""

import pytest

from app.domain.exceptions import AuthenticationError
from app.infrastructure.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPassword:
    """Tests for password hashing."""

    def test_hash_password_returns_hash(self):
        # Act
        hashed = hash_password("password123")

        # Assert
        assert hashed != "password123"
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        # Arrange
        hashed = hash_password("password123")

        # Act & Assert
        assert verify_password("password123", hashed) is True

    def test_verify_password_incorrect(self):
        # Arrange
        hashed = hash_password("password123")

        # Act & Assert
        assert verify_password("wrongpassword", hashed) is False


class TestJWT:
    """Tests for JWT tokens."""

    def test_create_access_token(self):
        # Act
        token = create_access_token("user-123")

        # Assert
        assert token is not None
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        # Act
        token = create_refresh_token("user-123")

        # Assert
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token_raises(self):
        # Act & Assert
        with pytest.raises(AuthenticationError):
            decode_token("invalid-token")

    def test_decode_tampered_token_raises(self):
        # Arrange
        token = create_access_token("user-123")
        tampered = token[:-5] + "XXXXX"

        # Act & Assert
        with pytest.raises(AuthenticationError):
            decode_token(tampered)
