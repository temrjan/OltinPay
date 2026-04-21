"""Integration tests for POST /api/v1/users/wallet.

Uses the existing test_user fixture (Telegram-authed user without a
wallet_address) and the in-memory SQLite DB wired in conftest.py.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

ENDPOINT = "/api/v1/users/wallet"
VALID_ADDRESS = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"


@pytest.mark.asyncio
async def test_register_wallet_success(
    client: AsyncClient, test_user: dict[str, Any]
) -> None:
    """First call binds the address and returns the updated user."""
    response = await client.post(
        ENDPOINT,
        json={"wallet_address": VALID_ADDRESS},
        headers=test_user["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    # Backend stores lowercase
    assert body["wallet_address"] == VALID_ADDRESS.lower()
    assert body["telegram_id"] == test_user["user"].telegram_id


@pytest.mark.asyncio
async def test_register_wallet_idempotent_same_address(
    client: AsyncClient, test_user: dict[str, Any]
) -> None:
    """Posting the same address twice should not conflict."""
    first = await client.post(
        ENDPOINT,
        json={"wallet_address": VALID_ADDRESS},
        headers=test_user["headers"],
    )
    assert first.status_code == 200

    second = await client.post(
        ENDPOINT,
        json={"wallet_address": VALID_ADDRESS},
        headers=test_user["headers"],
    )
    assert second.status_code == 200
    assert second.json()["wallet_address"] == VALID_ADDRESS.lower()


@pytest.mark.asyncio
async def test_register_wallet_rejects_rebind_to_different_address(
    client: AsyncClient, test_user: dict[str, Any]
) -> None:
    """Once bound, a different address is refused with 409."""
    await client.post(
        ENDPOINT,
        json={"wallet_address": VALID_ADDRESS},
        headers=test_user["headers"],
    )

    response = await client.post(
        ENDPOINT,
        json={"wallet_address": "0x" + "b" * 40},
        headers=test_user["headers"],
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_wallet_conflict_with_other_user(
    client: AsyncClient,
    test_user: dict[str, Any],
    second_user: dict[str, Any],
) -> None:
    """Another user can't claim an already-bound address."""
    first = await client.post(
        ENDPOINT,
        json={"wallet_address": VALID_ADDRESS},
        headers=test_user["headers"],
    )
    assert first.status_code == 200

    conflict = await client.post(
        ENDPOINT,
        json={"wallet_address": VALID_ADDRESS},
        headers=second_user["headers"],
    )
    assert conflict.status_code == 409


@pytest.mark.parametrize(
    "bad_address",
    [
        "",
        "not-an-address",
        "0x123",
        "a0A78aA9B9619fbc3bC12b5756442BD7A7D6779e",  # missing 0x
        "0x" + "z" * 40,  # invalid hex
        "0x" + "a" * 41,  # too long
    ],
)
@pytest.mark.asyncio
async def test_register_wallet_rejects_malformed(
    client: AsyncClient, test_user: dict[str, Any], bad_address: str
) -> None:
    response = await client.post(
        ENDPOINT,
        json={"wallet_address": bad_address},
        headers=test_user["headers"],
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_wallet_requires_auth(client: AsyncClient) -> None:
    response = await client.post(ENDPOINT, json={"wallet_address": VALID_ADDRESS})
    assert response.status_code in (401, 403)
