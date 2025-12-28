"""Order repository interface."""

from typing import Protocol
from uuid import UUID

from app.infrastructure.models import Order


class OrderRepositoryProtocol(Protocol):
    """Protocol for order repository."""

    async def create(self, order: Order) -> Order:
        """Create a new order."""
        ...

    async def get_by_id(self, order_id: UUID) -> Order | None:
        """Get order by ID."""
        ...

    async def update(self, order: Order) -> Order:
        """Update an existing order."""
        ...

    async def get_user_orders(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Order]:
        """Get orders for a user."""
        ...
