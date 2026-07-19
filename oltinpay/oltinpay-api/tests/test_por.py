"""Tests for the public PoR / rates endpoints and the authed /quote.

Chain reads are mocked with respx (sequential side_effect in call order — the
balances-on-chain test is the template).
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
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 — runtime type for fixtures
)

from src.config import settings
from src.indexer.models import ChainEvent, ChainEventType
from src.por.service import GRAMS_PER_OZ_1E8
from src.users.models import User

GRAMS_PER_GRAM_DECIMALS = 8


def _uint256(n: int) -> str:
    return f"{n & (2**256 - 1):064x}"


def _rpc(hex_body: str) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": 1, "result": "0x" + hex_body}


def _round_data(answer: int, updated_at: int, round_id: int = 1) -> str:
    return (
        _uint256(round_id)
        + _uint256(answer)
        + _uint256(0)
        + _uint256(updated_at)
        + _uint256(round_id)
    )


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
async def auth_user(db_session: AsyncSession) -> dict[str, Any]:
    user = User(
        id=uuid.uuid4(),
        telegram_id=51_000,
        oltin_id="poruser",
        language="en",
        wallet_address="0x" + "a" * 40,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {"user": user, "headers": {"Authorization": f"Bearer {_make_token(user.id)}"}}


@pytest.mark.asyncio
async def test_por_coverage_and_freshness(client: AsyncClient) -> None:
    reserve_answer = 1000 * 10**GRAMS_PER_GRAM_DECIMALS  # 1000 grams @ 8 dp
    updated_at = 1_800_000_000
    supply_wei = 500 * 10**18  # 500 OLTIN in circulation

    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(
            side_effect=[
                httpx.Response(200, json=_rpc(_round_data(reserve_answer, updated_at))),
                httpx.Response(200, json=_rpc(_uint256(GRAMS_PER_GRAM_DECIMALS))),
                httpx.Response(200, json=_rpc(_uint256(supply_wei))),
            ]
        )
        response = await client.get("/api/v1/por")

    assert response.status_code == 200
    body = response.json()
    assert body["reserve_answer"] == str(reserve_answer)
    assert body["reserve_grams"] == 1000.0
    assert body["oltin_supply"] == 500.0
    assert body["coverage_ratio"] == 2.0  # 1000 grams / 500 OLTIN
    assert body["reserve_updated_at"] == updated_at
    assert body["contracts"]["oltin"] == settings.oltin_contract_address
    assert body["contracts"]["reserve_attestor"] == settings.reserve_attestor_address


@pytest.mark.asyncio
async def test_por_coverage_null_when_no_supply(client: AsyncClient) -> None:
    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(
            side_effect=[
                httpx.Response(200, json=_rpc(_round_data(1000 * 10**8, 1_800_000_000))),
                httpx.Response(200, json=_rpc(_uint256(8))),
                httpx.Response(200, json=_rpc(_uint256(0))),  # zero supply
            ]
        )
        response = await client.get("/api/v1/por")

    assert response.status_code == 200
    assert response.json()["coverage_ratio"] is None


@pytest.mark.asyncio
async def test_por_history_from_indexer(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    db_session.add(
        ChainEvent(
            id=uuid.uuid4(),
            tx_hash="0x" + "c" * 64,
            log_index=0,
            event_type=ChainEventType.RESERVE_ANSWER.value,
            contract_address=settings.reserve_attestor_address.lower(),
            block_number=4242,
            answer=str(1000 * 10**8),
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/por/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 1
    assert history[0]["answer"] == str(1000 * 10**8)
    assert history[0]["block_number"] == 4242
    assert history[0]["tx_hash"] == "0x" + "c" * 64


@pytest.mark.asyncio
async def test_rates_live_feeds(client: AsyncClient) -> None:
    xau_answer = 3300 * 10**8  # $3300 / oz
    uzs_answer = 8000  # USD per UZS * 1e8 (=> 1 USD ~ 12500 UZS)

    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(
            side_effect=[
                httpx.Response(200, json=_rpc(_round_data(xau_answer, 111))),
                httpx.Response(200, json=_rpc(_uint256(8))),
                httpx.Response(200, json=_rpc(_round_data(uzs_answer, 222))),
                httpx.Response(200, json=_rpc(_uint256(8))),
            ]
        )
        response = await client.get("/api/v1/rates")

    assert response.status_code == 200
    body = response.json()
    assert body["xau_usd"]["answer"] == str(xau_answer)
    assert body["xau_usd"]["updated_at"] == 111
    assert body["uzs_usd"]["answer"] == str(uzs_answer)
    expected_price = (10**18 * xau_answer * 10**8) // (GRAMS_PER_OZ_1E8 * uzs_answer)
    assert body["oltin_price_uzd"] == expected_price / 10**18


@pytest.mark.asyncio
async def test_quote_buy_estimate(
    client: AsyncClient, auth_user: dict[str, Any]
) -> None:
    xau_answer = 3300 * 10**8
    uzs_answer = 8000

    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(
            side_effect=[
                httpx.Response(200, json=_rpc(_round_data(xau_answer, 111))),
                httpx.Response(200, json=_rpc(_round_data(uzs_answer, 222))),
            ]
        )
        response = await client.get(
            "/api/v1/quote?side=buy&amount=100", headers=auth_user["headers"]
        )

    assert response.status_code == 200
    body = response.json()
    assert body["side"] == "buy"
    assert body["estimated_out_symbol"] == "OLTIN"
    expected_out_wei = (100 * 10**18 * uzs_answer * GRAMS_PER_OZ_1E8) // (
        10**8 * xau_answer
    )
    assert body["estimated_out_wei"] == str(expected_out_wei)


@pytest.mark.asyncio
async def test_quote_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/quote")
    assert response.status_code in (401, 403)
