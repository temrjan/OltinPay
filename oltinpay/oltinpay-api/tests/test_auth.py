"""Auth module tests."""

import pytest
from httpx import AsyncClient


class TestAuthEndpoints:
    """Tests for auth endpoints."""

    @pytest.mark.asyncio
    async def test_telegram_auth_invalid_init_data(self, client: AsyncClient):
        """Test auth with invalid init_data returns 401."""
        response = await client.post(
            "/api/v1/auth/telegram",
            json={"init_data": "invalid_data"},
        )

        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_telegram_auth_empty_init_data(self, client: AsyncClient):
        """Test auth with empty init_data returns 401."""
        response = await client.post(
            "/api/v1/auth/telegram",
            json={"init_data": ""},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_telegram_auth_missing_init_data(self, client: AsyncClient):
        """Test auth without init_data returns 422."""
        response = await client.post(
            "/api/v1/auth/telegram",
            json={},
        )

        assert response.status_code == 422


class TestTokenValidation:
    """Tests for token validation."""

    @pytest.mark.asyncio
    async def test_valid_token_access(self, client: AsyncClient, test_user):
        """Test that valid token grants access."""
        response = await client.get(
            "/api/v1/users/me",
            headers=test_user["headers"],
        )

        assert response.status_code == 200
        assert response.json()["oltin_id"] == "testuser"

    @pytest.mark.asyncio
    async def test_invalid_token_denied(self, client: AsyncClient):
        """Test that invalid token is rejected."""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_token_denied(self, client: AsyncClient):
        """Test that missing token is rejected."""
        response = await client.get("/api/v1/users/me")

        assert response.status_code == 401
