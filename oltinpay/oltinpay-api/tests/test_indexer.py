"""Tests for the chain indexer — idempotent upsert, decode, and the tx feed."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx
import pytest
import respx
from sqlalchemy import func, select

from src.config import settings
from src.indexer import service
from src.indexer.models import ChainEvent, ChainEventType
from src.indexer.poller import MINTED_TOPIC, poll_once

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

WALLET = "0x" + "a" * 40


def _uint256(n: int) -> str:
    return f"{n:064x}"


def _topic_addr(addr: str) -> str:
    return "0x" + "0" * 24 + addr[2:].lower()


async def _count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(ChainEvent))
    return int(result.scalar() or 0)


@pytest.mark.asyncio
async def test_record_event_idempotent_on_tx_and_log_index(
    db_session: AsyncSession,
) -> None:
    kwargs = {
        "tx_hash": "0x" + "b" * 64,
        "log_index": 0,
        "event_type": ChainEventType.UZD_MINTED.value,
        "contract_address": settings.uzd_contract_address.lower(),
        "block_number": 100,
        "to_address": WALLET,
        "amount_wei": str(10**18),
    }
    first = await service.record_event(db_session, **kwargs)
    second = await service.record_event(db_session, **kwargs)  # exact duplicate

    assert first is True
    assert second is False
    assert await _count(db_session) == 1


@pytest.mark.asyncio
async def test_record_event_distinct_log_index_inserts_two(
    db_session: AsyncSession,
) -> None:
    base = {
        "tx_hash": "0x" + "b" * 64,
        "event_type": ChainEventType.UZD_TRANSFER.value,
        "contract_address": settings.uzd_contract_address.lower(),
        "block_number": 100,
    }
    assert await service.record_event(db_session, log_index=0, **base) is True
    assert await service.record_event(db_session, log_index=1, **base) is True
    assert await _count(db_session) == 2


@pytest.mark.asyncio
async def test_get_transactions_direction_and_links(db_session: AsyncSession) -> None:
    await service.record_event(
        db_session,
        tx_hash="0x" + "1" * 64,
        log_index=0,
        event_type=ChainEventType.UZD_MINTED.value,
        contract_address=settings.uzd_contract_address.lower(),
        block_number=10,
        to_address=WALLET,
        amount_wei="5",
    )
    await service.record_event(
        db_session,
        tx_hash="0x" + "2" * 64,
        log_index=0,
        event_type=ChainEventType.UZD_TRANSFER.value,
        contract_address=settings.uzd_contract_address.lower(),
        block_number=20,
        from_address=WALLET,
        to_address="0x" + "c" * 40,
        amount_wei="3",
    )
    await db_session.commit()

    txs = await service.get_transactions(db_session, WALLET)
    assert len(txs) == 2
    # Newest (higher block) first.
    assert txs[0].block_number == 20
    assert txs[0].direction == "out"
    assert txs[1].direction == "in"
    assert txs[0].explorer_url.endswith("0x" + "2" * 64)


@pytest.mark.asyncio
async def test_poll_once_decodes_and_is_idempotent(db_session: AsyncSession) -> None:
    head = 1000
    amount = 42 * 10**18
    minted_log = {
        "transactionHash": "0x" + "e" * 64,
        "logIndex": "0x0",
        "blockNumber": hex(head),
        "address": settings.uzd_contract_address.lower(),
        "topics": [MINTED_TOPIC, _topic_addr(WALLET)],
        "data": "0x" + _uint256(amount) + _uint256(1_800_000_000),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        method = body["method"]
        if method == "eth_blockNumber":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": hex(head)})
        if method == "eth_getLogs":
            address = body["params"][0]["address"]
            logs = [minted_log] if address == settings.uzd_contract_address.lower() else []
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": logs})
        raise AssertionError(f"unexpected method {method}")

    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(side_effect=handler)
        async with httpx.AsyncClient() as http_client:
            new_first = await poll_once(db_session, http_client)
            await db_session.commit()
            # Second pass: cursor has advanced past head -> nothing new.
            new_second = await poll_once(db_session, http_client)
            await db_session.commit()

    assert new_first == 1
    assert new_second == 0
    assert await _count(db_session) == 1

    event = (await db_session.execute(select(ChainEvent))).scalar_one()
    assert event.event_type == ChainEventType.UZD_MINTED.value
    assert event.to_address == WALLET
    assert event.amount_wei == str(amount)
    assert event.block_number == head
