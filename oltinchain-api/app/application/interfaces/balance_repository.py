"""Balance repository interface."""

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.infrastructure.models import Balance


class BalanceRepositoryProtocol(Protocol):
    """Protocol for balance repository."""

    async def get_or_create(self, user_id: UUID, asset: str) -> Balance:
        """Get balance or create if not exists."""
        ...

    async def get_user_balances(self, user_id: UUID) -> list[Balance]:
        """Get all balances for a user."""
        ...

    async def add_available(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Add to available balance."""
        ...

    async def subtract_available(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Subtract from available balance. Raises if insufficient."""
        ...

    async def lock_funds(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Move funds from available to locked."""
        ...

    async def unlock_funds(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Move funds from locked to available."""
        ...

    async def release_locked(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Remove from locked (after successful tx)."""
        ...
