"""Integration tests for GET /api/v1/balances.

The backend reads balances from zkSync Era via RPC — respx mocks the
single eth_call endpoint and issues three sequential responses for
OLTIN balanceOf, UZD balanceOf, and staking.getStakeInfo.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.users.models import User

ENDPOINT = "/api/v1/balances"
WALLET = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"


def _uint256(n: int) -> str:
    return f"{n:064x}"


def _rpc_response(hex_body: str) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": 1, "result": "0x" + hex_body}


def _make_token(user_id: uuid.UUID) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "access",
        },
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


@pytest_asyncio.fixture
async def wallet_user(db_session: AsyncSession) -> dict[str, Any]:
    """A user who has completed onboarding and has a wallet_address."""
    user = User(
        id=uuid.uuid4(),
        telegram_id=42_000,
        oltin_id="walletuser",
        language="en",
        wallet_address=WALLET.lower(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {
        "user": user,
        "headers": {"Authorization": f"Bearer {_make_token(user.id)}"},
    }


@pytest_asyncio.fixture
async def no_wallet_user(db_session: AsyncSession) -> dict[str, Any]:
    """A user who has NOT completed onboarding yet."""
    user = User(
        id=uuid.uuid4(),
        telegram_id=43_000,
        oltin_id="nowalletuser",
        language="en",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {
        "user": user,
        "headers": {"Authorization": f"Bearer {_make_token(user.id)}"},
    }


@pytest.mark.asyncio
async def test_get_balances_returns_on_chain_values(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    oltin_wei = 7 * 10**18
    uzd_wei = 1000 * 10**18
    stake_principal = 100 * 10**18
    stake_unlocked = 50 * 10**18
    stake_pending = 5 * 10**17
    stake_lot_count = 2
    stake_next_unlock = 1_761_000_000
    stake_body = (
        _uint256(stake_principal)
        + _uint256(stake_unlocked)
        + _uint256(stake_pending)
        + _uint256(stake_lot_count)
        + _uint256(stake_next_unlock)
    )

    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(
            side_effect=[
                httpx.Response(200, json=_rpc_response(_uint256(oltin_wei))),
                httpx.Response(200, json=_rpc_response(_uint256(uzd_wei))),
                httpx.Response(200, json=_rpc_response(stake_body)),
            ]
        )
        response = await client.get(ENDPOINT, headers=wallet_user["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["wallet_address"] == WALLET.lower()
    assert body["wallet"]["oltin_wei"] == str(oltin_wei)
    assert body["wallet"]["uzd_wei"] == str(uzd_wei)
    assert body["staking"]["total_principal_wei"] == str(stake_principal)
    assert body["staking"]["unlocked_wei"] == str(stake_unlocked)
    assert body["staking"]["pending_reward_wei"] == str(stake_pending)
    assert body["staking"]["lot_count"] == stake_lot_count
    assert body["staking"]["next_unlock_at"] == stake_next_unlock


@pytest.mark.asyncio
async def test_get_balances_rejects_user_without_wallet(
    client: AsyncClient, no_wallet_user: dict[str, Any]
) -> None:
    response = await client.get(ENDPOINT, headers=no_wallet_user["headers"])
    assert response.status_code == 400
    assert "Wallet address" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_balances_requires_auth(client: AsyncClient) -> None:
    response = await client.get(ENDPOINT)
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_balances_handles_zero_everywhere(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """A freshly-onboarded user with zero balances everywhere."""
    zero_stake = _uint256(0) * 5
    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(
            side_effect=[
                httpx.Response(200, json=_rpc_response(_uint256(0))),
                httpx.Response(200, json=_rpc_response(_uint256(0))),
                httpx.Response(200, json=_rpc_response(zero_stake)),
            ]
        )
        response = await client.get(ENDPOINT, headers=wallet_user["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["wallet"]["oltin_wei"] == "0"
    assert body["wallet"]["uzd_wei"] == "0"
    assert body["staking"]["total_principal_wei"] == "0"
    assert body["staking"]["lot_count"] == 0
