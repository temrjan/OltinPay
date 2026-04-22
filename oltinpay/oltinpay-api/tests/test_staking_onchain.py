"""Integration tests for /api/v1/staking — on-chain read-only view."""

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
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002  — runtime type for fixture
)

from src.config import settings
from src.users.models import User

ENDPOINT = "/api/v1/staking"
WALLET = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"


def _uint256(n: int) -> str:
    return f"{n:064x}"


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
    user = User(
        id=uuid.uuid4(),
        telegram_id=88_000,
        oltin_id="stakeuser",
        language="en",
        wallet_address=WALLET.lower(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {"user": user, "headers": {"Authorization": f"Bearer {_make_token(user.id)}"}}


@pytest_asyncio.fixture
async def no_wallet_user(db_session: AsyncSession) -> dict[str, Any]:
    user = User(
        id=uuid.uuid4(),
        telegram_id=89_000,
        oltin_id="unboarded",
        language="en",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {"user": user, "headers": {"Authorization": f"Bearer {_make_token(user.id)}"}}


@pytest.mark.asyncio
async def test_get_staking_info_returns_on_chain_values(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    principal = 100 * 10**18
    unlocked = 40 * 10**18
    pending = 5 * 10**17
    lot_count = 2
    next_unlock = 1_761_000_000
    body = (
        _uint256(principal)
        + _uint256(unlocked)
        + _uint256(pending)
        + _uint256(lot_count)
        + _uint256(next_unlock)
    )

    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(
            return_value=httpx.Response(
                200, json={"jsonrpc": "2.0", "id": 1, "result": "0x" + body}
            )
        )
        response = await client.get(ENDPOINT, headers=wallet_user["headers"])

    assert response.status_code == 200
    payload = response.json()
    assert payload["wallet_address"] == WALLET.lower()
    assert payload["total_principal_wei"] == str(principal)
    assert payload["unlocked_wei"] == str(unlocked)
    assert payload["pending_reward_wei"] == str(pending)
    assert payload["lot_count"] == lot_count
    assert payload["next_unlock_at"] == next_unlock
    assert payload["apy_bps"] == 700
    assert payload["lock_period_days"] == 7


@pytest.mark.asyncio
async def test_get_staking_info_rejects_without_wallet(
    client: AsyncClient, no_wallet_user: dict[str, Any]
) -> None:
    response = await client.get(ENDPOINT, headers=no_wallet_user["headers"])
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_staking_info_requires_auth(client: AsyncClient) -> None:
    response = await client.get(ENDPOINT)
    assert response.status_code in (401, 403)
