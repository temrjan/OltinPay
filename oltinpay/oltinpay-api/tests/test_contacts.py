"""Contacts module tests."""

import pytest
from httpx import AsyncClient


class TestRecentContacts:
    """Tests for recent contacts endpoint."""

    @pytest.mark.asyncio
    async def test_get_recent_contacts_empty(self, client: AsyncClient, test_user):
        """Test getting recent contacts with no transfers."""
        response = await client.get(
            "/api/v1/contacts/recent",
            headers=test_user["headers"],
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_recent_contacts_unauthorized(self, client: AsyncClient):
        """Test getting recent contacts without auth fails."""
        response = await client.get("/api/v1/contacts/recent")

        assert response.status_code == 401


class TestFavoriteContacts:
    """Tests for favorite contacts CRUD."""

    @pytest.mark.asyncio
    async def test_get_favorites_empty(self, client: AsyncClient, test_user):
        """Test getting favorites when empty."""
        response = await client.get(
            "/api/v1/contacts/favorites",
            headers=test_user["headers"],
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_add_favorite(self, client: AsyncClient, test_user, _second_user):
        """Test adding a contact to favorites."""
        response = await client.post(
            "/api/v1/contacts/favorites",
            headers=test_user["headers"],
            json={"oltin_id": "seconduser"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["oltin_id"] == "@seconduser"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_add_favorite_with_at_sign(
        self, client: AsyncClient, test_user, _second_user
    ):
        """Test adding favorite with @ prefix."""
        response = await client.post(
            "/api/v1/contacts/favorites",
            headers=test_user["headers"],
            json={"oltin_id": "@seconduser"},
        )

        assert response.status_code == 201
        assert response.json()["oltin_id"] == "@seconduser"

    @pytest.mark.asyncio
    async def test_add_favorite_self(self, client: AsyncClient, test_user):
        """Test adding yourself to favorites fails."""
        response = await client.post(
            "/api/v1/contacts/favorites",
            headers=test_user["headers"],
            json={"oltin_id": "testuser"},
        )

        assert response.status_code == 400
        assert "yourself" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_favorite_nonexistent(self, client: AsyncClient, test_user):
        """Test adding nonexistent user to favorites fails."""
        response = await client.post(
            "/api/v1/contacts/favorites",
            headers=test_user["headers"],
            json={"oltin_id": "nonexistent"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_favorite_duplicate(
        self, client: AsyncClient, test_user, _second_user
    ):
        """Test adding same contact twice fails."""
        # Add first time
        await client.post(
            "/api/v1/contacts/favorites",
            headers=test_user["headers"],
            json={"oltin_id": "seconduser"},
        )

        # Try to add again
        response = await client.post(
            "/api/v1/contacts/favorites",
            headers=test_user["headers"],
            json={"oltin_id": "seconduser"},
        )

        assert response.status_code == 409
        assert "already" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_remove_favorite(self, client: AsyncClient, test_user, _second_user):
        """Test removing contact from favorites."""
        # Add favorite
        add_response = await client.post(
            "/api/v1/contacts/favorites",
            headers=test_user["headers"],
            json={"oltin_id": "seconduser"},
        )
        favorite_id = add_response.json()["id"]

        # Remove favorite
        response = await client.delete(
            f"/api/v1/contacts/favorites/{favorite_id}",
            headers=test_user["headers"],
        )

        assert response.status_code == 204

        # Verify removed
        list_response = await client.get(
            "/api/v1/contacts/favorites",
            headers=test_user["headers"],
        )
        assert list_response.json() == []

    @pytest.mark.asyncio
    async def test_remove_favorite_not_found(self, client: AsyncClient, test_user):
        """Test removing nonexistent favorite fails."""
        response = await client.delete(
            "/api/v1/contacts/favorites/00000000-0000-0000-0000-000000000000",
            headers=test_user["headers"],
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_other_user_favorite(
        self, client: AsyncClient, test_user, _second_user
    ):
        """Test removing another user's favorite fails."""
        # Add favorite as _second_user
        add_response = await client.post(
            "/api/v1/contacts/favorites",
            headers=_second_user["headers"],
            json={"oltin_id": "testuser"},
        )
        favorite_id = add_response.json()["id"]

        # Try to remove as test_user
        response = await client.delete(
            f"/api/v1/contacts/favorites/{favorite_id}",
            headers=test_user["headers"],
        )

        assert response.status_code == 404
