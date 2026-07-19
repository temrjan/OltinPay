"""Chain event model — the indexer's idempotent event store.

One row per on-chain log, deduplicated by UNIQUE(tx_hash, log_index). Feeds
``GET /transactions`` and ``GET /por/history``.

Accepted limitation (spec §5): this is a simple last-N poller — not reorg-safe
and it does not backfill. Rows written during a reorged block are NOT rolled
back. Acceptable for the testnet demo only.
"""

from __future__ import annotations

from datetime import (
    datetime,  # noqa: TC003 — required at runtime for SQLAlchemy Mapped
)
from enum import StrEnum
from uuid import UUID  # noqa: TC003 — required at runtime for SQLAlchemy Mapped

from sqlalchemy import BigInteger, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class ChainEventType(StrEnum):
    """The on-chain events the indexer records."""

    UZD_MINTED = "uzd_minted"
    UZD_ADMIN_BURNED = "uzd_admin_burned"
    UZD_TRANSFER = "uzd_transfer"
    OLTIN_MINTED = "oltin_minted"
    OLTIN_TRANSFER = "oltin_transfer"
    RESERVE_ANSWER = "reserve_answer"


class ChainEvent(Base):
    """A single decoded on-chain log."""

    __tablename__ = "chain_events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    log_index: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # Transfer / mint / burn participants (null for AnswerPosted).
    from_address: Mapped[str | None] = mapped_column(String(42), nullable=True, index=True)
    to_address: Mapped[str | None] = mapped_column(String(42), nullable=True, index=True)
    amount_wei: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # AnswerPosted payload (null for token events); stored as text for int256.
    answer: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("tx_hash", "log_index", name="uq_chain_event_tx_log"),
    )

    def __repr__(self) -> str:
        return (
            f"<ChainEvent(type={self.event_type}, tx_hash={self.tx_hash}, "
            f"log_index={self.log_index})>"
        )
