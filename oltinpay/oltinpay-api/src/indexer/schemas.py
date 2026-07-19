"""Indexer-backed transaction feed schemas."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — runtime type for Pydantic field

from pydantic import BaseModel


class TransactionItem(BaseModel):
    """One on-chain event involving the user's wallet."""

    tx_hash: str
    event_type: str
    direction: str  # "in" | "out" | "self"
    block_number: int
    from_address: str | None
    to_address: str | None
    amount_wei: str | None
    explorer_url: str
    indexed_at: datetime
