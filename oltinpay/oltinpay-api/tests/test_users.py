"""Users module tests."""

import pytest
from httpx import AsyncClient


class TestUserProfile:
    """Tests for user profile endpoints."""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, test_user):
        """Test getting current user info."""
        response = await client.get(
            "/api/v1/users/me",
            headers=test_user["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["oltin_id"] == "testuser"
        assert data["telegram_id"] == 123456789
        assert data["language"] == "uz"

    @pytest.mark.asyncio
    async def test_update_user_language(self, client: AsyncClient, test_user):
        """Test updating user language."""
        response = await client.patch(
            "/api/v1/users/me",
            headers=test_user["headers"],
            json={"language": "ru"},
        )

        assert response.status_code == 200
        assert response.json()["language"] == "ru"

    @pytest.mark.asyncio
    async def test_update_user_invalid_language(self, client: AsyncClient, test_user):
        """Test updating with invalid language fails."""
        response = await client.patch(
            "/api/v1/users/me",
            headers=test_user["headers"],
            json={"language": "invalid"},
        )

        assert response.status_code == 422


class TestOltinId:
    """Tests for oltin_id management."""

    @pytest.mark.asyncio
    async def test_set_oltin_id_already_custom(self, client: AsyncClient, test_user):
        """Test setting oltin_id when already custom fails."""
        # testuser already has custom oltin_id (not user_*)
        response = await client.post(
            "/api/v1/users/oltin-id",
            headers=test_user["headers"],
            json={"oltin_id": "newid"},
        )

        assert response.status_code == 409
        assert "already set" in response.json()["detail"]


class TestUserSearch:
    """Tests for user search."""

    @pytest.mark.asyncio
    async def test_search_users(self, client: AsyncClient, test_user, _second_user):
        """Test searching users by oltin_id prefix."""
        response = await client.get(
            "/api/v1/users/search",
            params={"q": "test"},
            headers=test_user["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(u["oltin_id"] == "testuser" for u in data)

    @pytest.mark.asyncio
    async def test_search_users_no_results(self, client: AsyncClient, test_user):
        """Test searching with no matches returns empty list."""
        response = await client.get(
            "/api/v1/users/search",
            params={"q": "nonexistent"},
            headers=test_user["headers"],
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_search_users_empty_query(self, client: AsyncClient, test_user):
        """Test search with empty query fails."""
        response = await client.get(
            "/api/v1/users/search",
            params={"q": ""},
            headers=test_user["headers"],
        )

        assert response.status_code == 422
