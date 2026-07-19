"""Public PoR / rates / quote schemas (snake_case, like the user API)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — runtime type for Pydantic field
from enum import StrEnum

from pydantic import BaseModel


class QuoteSide(StrEnum):
    """Direction of a quote."""

    BUY = "buy"  # spend UZD, receive OLTIN
    SELL = "sell"  # spend OLTIN, receive UZD


class PorContractAddresses(BaseModel):
    """The on-chain contracts the PoR dashboard reads."""

    oltin: str
    uzd: str
    reserve_attestor: str
    exchange: str


class PorResponse(BaseModel):
    """Proof-of-reserve snapshot from the live chain."""

    reserve_answer: str  # raw ReserveAttestor answer (feed units)
    reserve_decimals: int
    reserve_grams: float  # answer / 10**decimals
    reserve_updated_at: int  # unix seconds; 0 = never posted
    oltin_total_supply_wei: str
    oltin_decimals: int
    oltin_supply: float  # supply / 10**18 (== OLTIN in circulation)
    # 1 OLTIN == 1 gram of gold, so coverage = reserve_grams / oltin_supply.
    # >= 1.0 means fully backed. null when nothing is in circulation.
    coverage_ratio: float | None
    contracts: PorContractAddresses


class PorHistoryItem(BaseModel):
    """A single reserve attestation seen by the indexer."""

    answer: str
    block_number: int
    tx_hash: str
    indexed_at: datetime


class FeedReading(BaseModel):
    """One price feed's live reading."""

    answer: str
    decimals: int
    updated_at: int


class RatesResponse(BaseModel):
    """Live XAU/USD and UZS/USD feed readings + derived OLTIN price."""

    xau_usd: FeedReading
    uzs_usd: FeedReading
    oltin_price_uzd: float  # UZS per 1 OLTIN (1 gram of gold)


class QuoteResponse(BaseModel):
    """A buy/sell price preview derived from the XAU + UZS feeds."""

    oltin_price_uzd: float  # UZS per 1 OLTIN
    xau_answer: str
    uzs_answer: str
    xau_updated_at: int
    uzs_updated_at: int
    side: QuoteSide | None = None
    amount: float | None = None
    estimated_out: float | None = None
    estimated_out_wei: str | None = None
    estimated_out_symbol: str | None = None
