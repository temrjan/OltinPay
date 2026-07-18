"""Indexer persistence + read helpers.

``record_event`` is the idempotent upsert used by the poller — it relies on the
UNIQUE(tx_hash, log_index) constraint (via a SAVEPOINT) so a re-seen log is a
no-op. ``get_transactions`` powers GET /api/v1/transactions.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from src.indexer.models import ChainEvent
from src.indexer.schemas import TransactionItem

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

EXPLORER_TX_BASE = "https://sepolia.explorer.zksync.io/tx/"


def explorer_url(tx_hash: str) -> str:
    """zkSync Sepolia explorer link for a transaction hash."""
    return f"{EXPLORER_TX_BASE}{tx_hash}"


async def record_event(
    db: AsyncSession,
    *,
    tx_hash: str,
    log_index: int,
    event_type: str,
    contract_address: str,
    block_number: int,
    from_address: str | None = None,
    to_address: str | None = None,
    amount_wei: str | None = None,
    answer: str | None = None,
) -> bool:
    """Insert a chain event idempotently.

    Returns True if a new row was written, False if (tx_hash, log_index) was
    already present. The UNIQUE constraint is the real guard — a SAVEPOINT keeps
    the outer transaction usable when the duplicate insert raises IntegrityError.
    """
    event = ChainEvent(
        id=uuid.uuid4(),
        tx_hash=tx_hash,
        log_index=log_index,
        event_type=event_type,
        contract_address=contract_address,
        block_number=block_number,
        from_address=from_address,
        to_address=to_address,
        amount_wei=amount_wei,
        answer=answer,
    )
    try:
        async with db.begin_nested():
            db.add(event)
            await db.flush()
    except IntegrityError:
        return False
    return True


def _direction(from_address: str | None, to_address: str | None, wallet: str) -> str:
    is_from = from_address == wallet
    is_to = to_address == wallet
    if is_from and is_to:
        return "self"
    if is_to:
        return "in"
    return "out"


async def get_transactions(
    db: AsyncSession, wallet_address: str, limit: int = 50
) -> list[TransactionItem]:
    """Chain events touching ``wallet_address``, newest first."""
    wallet = wallet_address.lower()
    result = await db.execute(
        select(ChainEvent)
        .where(
            or_(
                ChainEvent.from_address == wallet,
                ChainEvent.to_address == wallet,
            )
        )
        .order_by(ChainEvent.block_number.desc())
        .limit(limit)
    )
    return [
        TransactionItem(
            tx_hash=event.tx_hash,
            event_type=event.event_type,
            direction=_direction(event.from_address, event.to_address, wallet),
            block_number=event.block_number,
            from_address=event.from_address,
            to_address=event.to_address,
            amount_wei=event.amount_wei,
            explorer_url=explorer_url(event.tx_hash),
            indexed_at=event.created_at,
        )
        for event in result.scalars().all()
    ]
