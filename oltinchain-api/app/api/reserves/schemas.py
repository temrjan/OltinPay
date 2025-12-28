"""Reserves API schemas."""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PhysicalGoldInfo(BaseModel):
    """Physical gold holdings info."""
    total_grams: str
    total_bars: int


class TokenSupplyInfo(BaseModel):
    """Token supply info."""
    total_supply: str
    contract_address: str | None


class CoverageInfo(BaseModel):
    """Coverage ratio info."""
    ratio: str
    percentage: str
    status: str  # fully_backed, nearly_backed, under_backed


class ProofOfReservesResponse(BaseModel):
    """Proof of Reserves response."""
    physical_gold: PhysicalGoldInfo
    token_supply: TokenSupplyInfo
    coverage: CoverageInfo
    verified_at: str


class GoldBarResponse(BaseModel):
    """Gold bar details."""
    id: str
    serial_number: str
    weight_grams: Decimal
    purity: Decimal
    vault_location: str | None
    acquired_at: datetime | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoldBarListResponse(BaseModel):
    """List of gold bars."""
    bars: list[GoldBarResponse]
    total: int
    limit: int
    offset: int
