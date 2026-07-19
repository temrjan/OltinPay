"""Per-user advisory locking for the solvency-cap critical section (BLOCKER B1).

The deposit-backed withdrawal cap sums a user's deposits vs withdrawals and then
acts on the result. Under Postgres READ COMMITTED two concurrent withdrawals for
the same user do NOT see each other's uncommitted rows, so both could pass the
cap and together burn more than the user deposited (BLOCKER B1). We serialize all
create/confirm operations for a given user with a transaction-scoped Postgres
advisory lock — held until the surrounding transaction commits or rolls back — so
the read-then-act check runs one-at-a-time per user and is race-free.

SQLite (the unit-test suite) has no advisory locks and serializes writers anyway,
so this is a no-op there; the real Postgres concurrency guarantee is proven by
tests/test_concurrency_pg.py (red without this lock, green with it).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


async def lock_user(db: AsyncSession, user_id: UUID) -> None:
    """Take a transaction-scoped per-user advisory lock (Postgres only).

    No-op on non-Postgres dialects (SQLite tests). Must be called inside the
    transaction that performs the cap check + mutation; the lock releases when
    that transaction ends.
    """
    if db.get_bind().dialect.name != "postgresql":
        return
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(cast(:uid AS text), 0))"),
        {"uid": str(user_id)},
    )
