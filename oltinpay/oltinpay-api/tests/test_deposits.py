"""Tests for the user deposit-intent endpoint — POST /api/v1/deposits.

A DEMO fiat on-ramp: it returns static bank requisites plus a per-user
reference and has no DB or on-chain effect (the actual UZD mint happens later
when the bank calls POST /api/v1/bank/deposits). These cover the authed happy
path, the auth requirement, and request validation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient  # noqa: TC002 — runtime type for fixtures
from jose import jwt
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 — runtime type for fixtures
)

from src.config import settings
from src.users.models import User

ENDPOINT = "/api/v1/deposits"
OLTIN_ID = "depuser"


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


@pytest.fixture
async def auth_headers(db_session: AsyncSession) -> dict[str, str]:
    user = User(
        id=uuid.uuid4(),
        telegram_id=81_000,
        oltin_id=OLTIN_ID,
        language="en",
    )
    db_session.add(user)
    await db_session.commit()
    return {"Authorization": f"Bearer {_make_token(user.id)}"}


@pytest.mark.asyncio
async def test_deposit_intent_returns_requisites(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        ENDPOINT, json={"amount_uzs": 5000}, headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["amount_uzs"] == 5000
    # The reference binds the user and amount so the bank can match the later
    # POST /api/v1/bank/deposits settlement.
    assert body["requisites"]["reference"] == f"OLTIN-{OLTIN_ID}-5000"
    assert body["requisites"]["bank_name"]
    assert body["requisites"]["account_number"]
    assert body["requisites"]["mfo"]
    assert "note" in body


@pytest.mark.asyncio
async def test_deposit_intent_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(ENDPOINT, json={"amount_uzs": 5000})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [0, -1])
async def test_deposit_intent_rejects_non_positive_amount(
    client: AsyncClient, auth_headers: dict[str, str], amount: int
) -> None:
    resp = await client.post(
        ENDPOINT, json={"amount_uzs": amount}, headers=auth_headers
    )
    assert resp.status_code == 422  # Field(gt=0)
