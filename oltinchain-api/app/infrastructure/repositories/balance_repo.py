"""Balance repository implementation."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import InsufficientBalanceError
from app.infrastructure.models import Balance


class BalanceRepository:
    """SQLAlchemy implementation of balance repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, user_id: UUID, asset: str) -> Balance:
        """Get balance or create if not exists."""
        result = await self.session.execute(
            select(Balance).where(
                Balance.user_id == user_id,
                Balance.asset == asset,
            )
        )
        balance = result.scalar_one_or_none()

        if not balance:
            balance = Balance(
                user_id=user_id,
                asset=asset,
                available=Decimal("0"),
                locked=Decimal("0"),
            )
            self.session.add(balance)
            await self.session.commit()
            await self.session.refresh(balance)

        return balance

    async def get_user_balances(self, user_id: UUID) -> list[Balance]:
        """Get all balances for a user."""
        result = await self.session.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
        return list(result.scalars().all())

    async def add_available(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Add to available balance."""
        balance = await self.get_or_create(user_id, asset)
        balance.available += amount
        await self.session.commit()
        await self.session.refresh(balance)
        return balance

    async def subtract_available(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Subtract from available balance. Raises if insufficient."""
        balance = await self.get_or_create(user_id, asset)

        if balance.available < amount:
            raise InsufficientBalanceError(
                f"Insufficient {asset} balance: have {balance.available}, need {amount}"
            )

        balance.available -= amount
        await self.session.commit()
        await self.session.refresh(balance)
        return balance

    async def lock_funds(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Move funds from available to locked."""
        balance = await self.get_or_create(user_id, asset)

        if balance.available < amount:
            raise InsufficientBalanceError(
                f"Insufficient {asset} to lock: have {balance.available}, need {amount}"
            )

        balance.available -= amount
        balance.locked += amount
        await self.session.commit()
        await self.session.refresh(balance)
        return balance

    async def unlock_funds(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Move funds from locked to available."""
        balance = await self.get_or_create(user_id, asset)
        balance.locked -= amount
        balance.available += amount
        await self.session.commit()
        await self.session.refresh(balance)
        return balance

    async def release_locked(self, user_id: UUID, asset: str, amount: Decimal) -> Balance:
        """Remove from locked (after successful tx)."""
        balance = await self.get_or_create(user_id, asset)
        balance.locked -= amount
        await self.session.commit()
        await self.session.refresh(balance)
        return balance
