"""Wallet API schemas."""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class BalanceItem(BaseModel):
    """Single asset balance."""
    available: Decimal
    locked: Decimal
    total: Decimal

    model_config = ConfigDict(from_attributes=True)


class WalletBalanceResponse(BaseModel):
    """Full wallet balance response."""
    uzs: BalanceItem
    oltin: BalanceItem
    wallet_address: str | None = None


class TransactionResponse(BaseModel):
    """Transaction history item."""
    id: str
    type: str  # buy, sell, deposit, withdraw, transfer
    asset: str
    amount: Decimal
    amount_uzs: Decimal | None = None
    amount_oltin: Decimal | None = None
    fee_uzs: Decimal | None = None
    tx_hash: str | None = None
    to_address: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    """List of transactions."""
    transactions: list[TransactionResponse]
    total: int
    limit: int
    offset: int


class SyncStatusResponse(BaseModel):
    """Blockchain sync status."""
    wallet_address: str
    on_chain_balance: Decimal | None = None
    local_available: Decimal | None = None
    local_locked: Decimal | None = None
    local_total: Decimal | None = None
    is_synced: bool
    discrepancy: Decimal | None = None
    error: str | None = None


class DepositRequest(BaseModel):
    """Deposit request (for testing)."""
    amount_uzs: Decimal


class DepositResponse(BaseModel):
    """Deposit response."""
    success: bool
    new_balance: Decimal
    message: str


class TransferRequest(BaseModel):
    """Transfer OLTIN to another wallet."""
    to_address: str = Field(min_length=42, max_length=42)
    amount: Decimal = Field(gt=0, description="Amount in grams")


class TransferResponse(BaseModel):
    """Transfer result."""
    success: bool
    tx_hash: str
    from_address: str
    to_address: str
    amount: Decimal
    message: str
