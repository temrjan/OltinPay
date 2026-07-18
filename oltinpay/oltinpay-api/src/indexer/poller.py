"""Background chain indexer — a deliberately simple last-N poller.

ACCEPTED LIMITATION (spec §5, logged loudly at startup): this poller reads logs
from ``max(indexed block)+1`` (or ``head - lookback`` on a cold start) up to the
current head every ``INDEXER_POLL_SEC`` seconds and upserts them idempotently by
(tx_hash, log_index). It is NOT reorg-safe and does NOT backfill history beyond
the lookback window. Acceptable for the testnet demo only; a reorg-aware,
backfilling indexer is out of scope.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import func, select

from src.config import settings
from src.database import async_session_maker
from src.indexer.models import ChainEvent, ChainEventType
from src.indexer.service import record_event
from src.infrastructure import chain_read

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Event topic0 hashes (keccak256 of the canonical event signature).
MINTED_TOPIC = "0x25b428dfde728ccfaddad7e29e4ac23c24ed7fd1a6e3e3f91894a9a073f5dfff"
ADMIN_BURNED_TOPIC = "0x0300fb1646762c86af728e4b346b04152b9e37f2a30f156dd9c464ab60a446d8"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ANSWER_POSTED_TOPIC = "0x6222799a52e6ff10a8054d1589b5069e4736b8a0c789750abef03e1dfdc837fc"


@dataclass(frozen=True, slots=True)
class _Monitor:
    """One (event_type, topic0, decode-kind) the indexer watches on a contract."""

    event_type: ChainEventType
    topic0: str
    kind: str  # "mint" | "burn" | "transfer" | "answer"


def _monitors() -> dict[str, list[_Monitor]]:
    """Watched contracts (lowercased address) -> the events to decode on each."""
    return {
        settings.uzd_contract_address.lower(): [
            _Monitor(ChainEventType.UZD_MINTED, MINTED_TOPIC, "mint"),
            _Monitor(ChainEventType.UZD_ADMIN_BURNED, ADMIN_BURNED_TOPIC, "burn"),
            _Monitor(ChainEventType.UZD_TRANSFER, TRANSFER_TOPIC, "transfer"),
        ],
        settings.oltin_contract_address.lower(): [
            _Monitor(ChainEventType.OLTIN_MINTED, MINTED_TOPIC, "mint"),
            _Monitor(ChainEventType.OLTIN_TRANSFER, TRANSFER_TOPIC, "transfer"),
        ],
        settings.reserve_attestor_address.lower(): [
            _Monitor(ChainEventType.RESERVE_ANSWER, ANSWER_POSTED_TOPIC, "answer"),
        ],
    }


def _addr_from_topic(topic: str) -> str:
    """Extract the 20-byte address packed in a 32-byte indexed topic."""
    return "0x" + topic[-40:].lower()


def _word(data: str, index: int) -> str:
    body = data[2:] if data.startswith("0x") else data
    return body[index * 64 : (index + 1) * 64]


def _decode_int256(word: str) -> int:
    value = int(word, 16)
    return value - 2**256 if value >= 2**255 else value


async def _from_block(db: AsyncSession, head: int) -> int:
    result = await db.execute(select(func.max(ChainEvent.block_number)))
    max_block: int | None = result.scalar()
    if max_block is None:
        return max(0, head - settings.indexer_lookback_blocks)
    return max_block + 1


async def _record_log(
    db: AsyncSession, address: str, monitor: _Monitor, log: dict[str, Any]
) -> bool:
    tx_hash = str(log["transactionHash"]).lower()
    log_index = int(str(log["logIndex"]), 16)
    block_number = int(str(log["blockNumber"]), 16)
    topics = [str(t).lower() for t in (log.get("topics") or [])]
    data = str(log.get("data", "0x"))

    from_address: str | None = None
    to_address: str | None = None
    amount_wei: str | None = None
    answer: str | None = None

    if monitor.kind == "mint":
        to_address = _addr_from_topic(topics[1])
        amount_wei = str(int(_word(data, 0), 16))
    elif monitor.kind == "burn":
        from_address = _addr_from_topic(topics[1])
        amount_wei = str(int(_word(data, 0), 16))
    elif monitor.kind == "transfer":
        from_address = _addr_from_topic(topics[1])
        to_address = _addr_from_topic(topics[2])
        amount_wei = str(int(_word(data, 0), 16))
    else:  # "answer"
        answer = str(_decode_int256(_word(data, 0)))

    return await record_event(
        db,
        tx_hash=tx_hash,
        log_index=log_index,
        event_type=monitor.event_type.value,
        contract_address=address,
        block_number=block_number,
        from_address=from_address,
        to_address=to_address,
        amount_wei=amount_wei,
        answer=answer,
    )


async def poll_once(db: AsyncSession, client: httpx.AsyncClient) -> int:
    """Fetch and record new logs once. Returns the count of newly-stored events.

    Does not commit — the caller owns the transaction boundary.
    """
    head = await chain_read.block_number(client=client)
    from_block = await _from_block(db, head)
    if from_block > head:
        return 0

    new_events = 0
    for address, monitors in _monitors().items():
        by_topic = {m.topic0: m for m in monitors}
        logs = await chain_read.get_logs(
            from_block=from_block,
            to_block=head,
            address=address,
            topics=[[m.topic0 for m in monitors]],
            client=client,
        )
        for log in logs:
            topics = log.get("topics") or []
            if not topics:
                continue
            monitor = by_topic.get(str(topics[0]).lower())
            if monitor is None:
                continue
            try:
                if await _record_log(db, address, monitor, log):
                    new_events += 1
            except (ValueError, KeyError, IndexError):
                logger.warning("indexer_skip_malformed_log tx=%s", log.get("transactionHash"))
    return new_events


class Indexer:
    """Owns the polling task; started/stopped from the FastAPI lifespan."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        logger.warning(
            "indexer_starting poll_sec=%s LIMITATION: last-N poller, NOT reorg-safe "
            "and does NOT backfill (testnet demo only)",
            settings.indexer_poll_sec,
        )
        self._stopped.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stopped.set()
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                async with (
                    async_session_maker() as db,
                    httpx.AsyncClient(timeout=20.0) as client,
                ):
                    count = await poll_once(db, client)
                    await db.commit()
                    if count:
                        logger.info("indexer_ingested events=%s", count)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("indexer_poll_failed")
            # Interruptible sleep: wakes immediately when stop() is called.
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    self._stopped.wait(), timeout=settings.indexer_poll_sec
                )


indexer = Indexer()
