"""Blockchain service interface."""

from decimal import Decimal
from typing import Protocol


class BlockchainServiceProtocol(Protocol):
    """Protocol for blockchain operations."""

    async def mint(self, to_address: str, grams: Decimal, order_id: str) -> str:
        """Mint tokens to address."""
        ...

    async def burn(self, from_address: str, grams: Decimal, order_id: str) -> str:
        """Burn tokens from address."""
        ...

    async def get_balance(self, address: str) -> Decimal:
        """Get token balance."""
        ...

    async def get_total_supply(self) -> Decimal:
        """Get total supply."""
        ...
