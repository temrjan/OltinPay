"""Order repository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import Order


class OrderRepository:
    """SQLAlchemy implementation of order repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, order: Order) -> Order:
        """Create a new order."""
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        """Get order by ID."""
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def update(self, order: Order) -> Order:
        """Update an existing order."""
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def get_user_orders(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Order]:
        """Get orders for a user, newest first."""
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
