"""Contacts module tests."""

from typing import Any

import pytest
from httpx import AsyncClient

from src.database import Base


class TestRemovedLedgerRoutes:
    """The retired ledger cannot be reached through the API or ORM."""

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", "/api/v1/transfers"),
            ("POST", "/api/v1/transfers"),
            ("GET", "/api/v1/transfers/00000000-0000-0000-0000-000000000000"),
            ("GET", "/api/v1/contacts/recent"),
        ],
    )
    async def test_removed_endpoint_returns_404(
        self,
        client: AsyncClient,
        test_user: dict[str, Any],
        method: str,
        path: str,
    ) -> None:
        response = await client.request(
            method,
            path,
            headers=test_user["headers"],
            json={"to_oltin_id": "testuser", "amount": "1"}
            if method == "POST"
            else None,
        )

        assert response.status_code == 404

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/transfers",
            "/api/v1/transfers/{transfer_id}",
            "/api/v1/contacts/recent",
        ],
    )
    async def test_openapi_omits_ledger_but_keeps_history_and_favorites(
        self, client: AsyncClient, path: str
    ) -> None:
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        paths = response.json()["paths"]
        assert "/api/v1/transactions" in paths
        assert "/api/v1/contacts/favorites" in paths
        assert path not in paths

    def test_orm_omits_transfers(self) -> None:
        assert "transfers" not in Base.metadata.tables


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
    async def test_add_favorite(self, client: AsyncClient, test_user, second_user):
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
        self, client: AsyncClient, test_user, second_user
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
        self, client: AsyncClient, test_user, second_user
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
    async def test_remove_favorite(self, client: AsyncClient, test_user, second_user):
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
        self, client: AsyncClient, test_user, second_user
    ):
        """Test removing another user's favorite fails."""
        # Add favorite as second_user
        add_response = await client.post(
            "/api/v1/contacts/favorites",
            headers=second_user["headers"],
            json={"oltin_id": "testuser"},
        )
        favorite_id = add_response.json()["id"]

        # Try to remove as test_user
        response = await client.delete(
            f"/api/v1/contacts/favorites/{favorite_id}",
            headers=test_user["headers"],
        )

        assert response.status_code == 404
