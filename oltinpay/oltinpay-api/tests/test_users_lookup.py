"""Integration tests for GET /api/v1/users/lookup.

Resolves a recipient ``oltin_id`` to their on-chain ``wallet_address`` so the
Mini App can sign a real P2P OLTIN transfer to the right address. Reuses the
test_user / second_user fixtures + in-memory SQLite from conftest.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

ENDPOINT = "/api/v1/users/lookup"
WALLET_ENDPOINT = "/api/v1/users/wallet"
VALID_ADDRESS = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"


@pytest.mark.usefixtures("second_user")
@pytest.mark.asyncio
async def test_lookup_found_without_wallet_returns_null(
    client: AsyncClient, test_user: dict[str, Any]
) -> None:
    """A resolvable user who never onboarded a wallet returns wallet_address=null
    (the client blocks the send with 'recipient has no wallet')."""
    response = await client.get(
        ENDPOINT, params={"oltin_id": "seconduser"}, headers=test_user["headers"]
    )
    assert response.status_code == 200
    body = response.json()
    assert body["oltin_id"] == "seconduser"
    assert body["wallet_address"] is None


@pytest.mark.asyncio
async def test_lookup_found_with_wallet(
    client: AsyncClient, test_user: dict[str, Any], second_user: dict[str, Any]
) -> None:
    """Once the recipient has bound a wallet, lookup returns its lowercase address."""
    bind = await client.post(
        WALLET_ENDPOINT,
        json={"wallet_address": VALID_ADDRESS},
        headers=second_user["headers"],
    )
    assert bind.status_code == 200

    response = await client.get(
        ENDPOINT, params={"oltin_id": "seconduser"}, headers=test_user["headers"]
    )
    assert response.status_code == 200
    body = response.json()
    assert body["oltin_id"] == "seconduser"
    assert body["wallet_address"] == VALID_ADDRESS.lower()


@pytest.mark.usefixtures("second_user")
@pytest.mark.parametrize("query", ["seconduser", "SECONDUSER", "@seconduser", "  seconduser  "])
@pytest.mark.asyncio
async def test_lookup_normalizes_oltin_id(
    client: AsyncClient, test_user: dict[str, Any], query: str
) -> None:
    """oltin_id is normalized (lowercase, strip, leading @) — same as search/bind."""
    response = await client.get(
        ENDPOINT, params={"oltin_id": query}, headers=test_user["headers"]
    )
    assert response.status_code == 200
    assert response.json()["oltin_id"] == "seconduser"


@pytest.mark.asyncio
async def test_lookup_not_found(
    client: AsyncClient, test_user: dict[str, Any]
) -> None:
    """An unknown oltin_id resolves to 404, not a null/empty 200."""
    response = await client.get(
        ENDPOINT, params={"oltin_id": "ghostuser"}, headers=test_user["headers"]
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_lookup_requires_auth(client: AsyncClient) -> None:
    """Resolving another user's address requires authentication."""
    response = await client.get(ENDPOINT, params={"oltin_id": "seconduser"})
    assert response.status_code in (401, 403)
