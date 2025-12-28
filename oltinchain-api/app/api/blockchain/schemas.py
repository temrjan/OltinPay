"""Blockchain API schemas."""

from pydantic import BaseModel, Field


class TokenInfoResponse(BaseModel):
    """Token info response."""

    name: str
    symbol: str
    decimals: int
    total_supply: str
    contract_address: str


class BalanceResponse(BaseModel):
    """Balance response."""

    address: str
    balance: str
    symbol: str = "OLTIN"


class MintRequest(BaseModel):
    """Mint request (admin only)."""

    to_address: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")
    amount_grams: str = Field(examples=["1.5"])
    order_id: str = Field(min_length=1, max_length=100)


class BurnRequest(BaseModel):
    """Burn request (admin only)."""

    from_address: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")
    amount_grams: str = Field(examples=["1.0"])
    order_id: str = Field(min_length=1, max_length=100)


class TransactionResponse(BaseModel):
    """Transaction response."""

    tx_hash: str
    status: str = "confirmed"
