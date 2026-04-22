"""Integration tests for /api/v1/welcome endpoints.

send_admin_mint is patched so the tests never touch the real RPC and
never require ADMIN_PRIVATE_KEY to be configured.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient  # noqa: TC002  — runtime type for fixture
from jose import jwt
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002  — runtime type for fixture
)

from src.config import settings
from src.users.models import User

CLAIM = "/api/v1/welcome/claim"
STATUS = "/api/v1/welcome/status"
WALLET = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"
FAKE_TX = "0x" + "b" * 64


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
        telegram_id=77_000,
        oltin_id="walletuser",
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
        telegram_id=78_000,
        oltin_id="nowallet",
        language="en",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {"user": user, "headers": {"Authorization": f"Bearer {_make_token(user.id)}"}}


@pytest.mark.asyncio
async def test_claim_success(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    with patch(
        "src.welcome.service.send_admin_mint",
        new=AsyncMock(return_value=FAKE_TX),
    ):
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["tx_hash"] == FAKE_TX
    assert body["amount_wei"] == str(1000 * 10**18)
    assert body["wallet_address"] == WALLET.lower()


@pytest.mark.asyncio
async def test_claim_rejects_without_wallet(
    client: AsyncClient, no_wallet_user: dict[str, Any]
) -> None:
    response = await client.post(CLAIM, headers=no_wallet_user["headers"])
    assert response.status_code == 400
    assert "Wallet address" in response.json()["detail"]


@pytest.mark.asyncio
async def test_claim_idempotent_conflict(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    with patch(
        "src.welcome.service.send_admin_mint",
        new=AsyncMock(return_value=FAKE_TX),
    ):
        first = await client.post(CLAIM, headers=wallet_user["headers"])
        assert first.status_code == 200

        second = await client.post(CLAIM, headers=wallet_user["headers"])
        assert second.status_code == 409


@pytest.mark.asyncio
async def test_claim_requires_auth(client: AsyncClient) -> None:
    response = await client.post(CLAIM)
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_status_unclaimed(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    response = await client.get(STATUS, headers=wallet_user["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["claimed"] is False
    assert body["tx_hash"] is None


@pytest.mark.asyncio
async def test_status_after_claim(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    with patch(
        "src.welcome.service.send_admin_mint",
        new=AsyncMock(return_value=FAKE_TX),
    ):
        await client.post(CLAIM, headers=wallet_user["headers"])

    response = await client.get(STATUS, headers=wallet_user["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["claimed"] is True
    assert body["tx_hash"] == FAKE_TX
