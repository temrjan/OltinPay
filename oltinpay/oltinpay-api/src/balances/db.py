"""Legacy DB helpers for balances — used by transfers/ and staking/.

These functions read the pre-v2 `balances` table (USD/OLTIN virtual
accounts). They'll be retired when `transfers/` and `staking/` are
moved to on-chain reads in week 5. Kept here so those modules keep
compiling during the migration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.balances.models import Balance

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


async def get_balance(
    db: AsyncSession,
    user_id: UUID,
    account_type: str,
    currency: str,
) -> Balance | None:
    """Fetch a single Balance row from the legacy DB-balance table."""
    result = await db.execute(
        select(Balance).where(
            Balance.user_id == user_id,
            Balance.account_type == account_type,
            Balance.currency == currency,
        )
    )
    return result.scalar_one_or_none()
