"""Postgres concurrency test for the deposit-backed solvency cap (BLOCKER B1).

The cap sums a user's deposits vs withdrawals then acts. Under Postgres READ
COMMITTED two concurrent withdrawals for one user do NOT see each other's
uncommitted rows; without the per-user advisory lock (``db_lock.lock_user``)
both pass the cap and together burn more than deposited.

This drives the race **deterministically** rather than hoping the event loop
interleaves two ``gather``-ed calls at the right instant (a natural-race test
passes even without the lock whenever the scheduler happens to serialize it —
a silent blind spot for exactly the regression we must catch). Instead:

  * Coroutine A enters ``create_withdrawal`` (takes the xact-scoped lock, reads
    the cap, inserts) and **holds its transaction open** — parked inside the
    critical section.
  * Coroutine B races for the same user in its own session. With the lock B must
    block on ``lock_user`` until A commits; without it B reads the stale cap and
    also succeeds.
  * We commit A, then observe B: with the lock B is cap-rejected (exactly one
    success); without it B already succeeded before A committed (two successes).

Needs a REAL Postgres — advisory locks are a no-op on SQLite, so the race is
invisible there (which is exactly why the original bug escaped the SQLite suite).
Skipped unless ``TEST_PG_URL`` is set.

Run:
    TEST_PG_URL=postgresql+asyncpg://test:test@localhost:55432/test \
        uv run pytest tests/test_concurrency_pg.py
"""

from __future__ import annotations

import asyncio
import importlib
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.bank.models import BankDeposit
from src.common.exceptions import BadRequestException
from src.config import settings
from src.database import Base
from src.users.models import User
from src.welcome import service as welcome_service
from src.withdrawals import service as withdrawals_service
from src.withdrawals.models import Withdrawal

PG_URL = os.environ.get("TEST_PG_URL")
pytestmark = pytest.mark.skipif(
    not PG_URL,
    reason="TEST_PG_URL not set (advisory locks need a real Postgres)",
)

UZD_DECIMALS = 18
DEPOSITED = 100


@pytest_asyncio.fixture
async def pg() -> tuple[async_sessionmaker[object], uuid.UUID]:
    # Populate Base.metadata with every table (side-effect import of model
    # modules not otherwise referenced here) before create_all.
    for _mod in ("src.balances.models", "src.indexer.models", "src.welcome.models"):
        importlib.import_module(_mod)
    engine = create_async_engine(PG_URL, pool_size=5, max_overflow=5)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    user_id = uuid.uuid4()
    async with maker() as s:
        s.add(
            User(
                id=user_id,
                telegram_id=111,
                oltin_id="capuser",
                wallet_address="0x" + "a" * 40,
                language="uz",
            )
        )
        await s.flush()
        s.add(
            BankDeposit(
                id=uuid.uuid4(),
                user_id=user_id,
                bank_tx_id="dep-1",
                amount_uzs=DEPOSITED,
                amount_wei=str(DEPOSITED * 10**UZD_DECIMALS),
                tx_hash="0xdep",
            )
        )
        await s.commit()

    try:
        yield maker, user_id
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


async def _try_withdraw(
    maker: async_sessionmaker[object], user_id: uuid.UUID, amount: int
) -> bool:
    """One withdrawal in its own session/transaction. True=ok, False=cap-rejected."""
    async with maker() as s:
        user = await s.get(User, user_id)
        try:
            await withdrawals_service.create_withdrawal(s, user, amount)
            await s.commit()
            return True
        except BadRequestException:
            await s.rollback()
            return False


@pytest.mark.asyncio
async def test_concurrent_withdrawals_respect_cap(
    pg: tuple[async_sessionmaker[object], uuid.UUID],
) -> None:
    """Two concurrent full-balance withdrawals -> exactly one succeeds.

    Deposited=100; both request 100. A parks inside the critical section holding
    the per-user lock; B races. With the lock B blocks until A commits and then
    sees available=0 (rejected); without the lock B reads the stale available=100
    and also succeeds (200 > 100 burnable) — which fails this test.
    """
    maker, user_id = pg

    # A: enter the critical section and hold the transaction open. create_withdrawal
    # flushes but never commits, so the xact-scoped advisory lock stays held by A.
    session_a = maker()
    try:
        user_a = await session_a.get(User, user_id)
        await withdrawals_service.create_withdrawal(session_a, user_a, DEPOSITED)

        # B races for the same user. Under the lock it must block on lock_user()
        # until A commits; without it, it runs to completion right now.
        b_task = asyncio.create_task(_try_withdraw(maker, user_id, DEPOSITED))

        # Let B reach the lock. This is a synchronization point, not flaky-masking:
        # the assertions are deterministic either way — the sleep only decides
        # *when* B proceeds, never *whether* it is rejected.
        await asyncio.sleep(0.5)
        b_finished_before_a_committed = b_task.done()

        await session_a.commit()  # releases the advisory lock
    finally:
        await session_a.close()

    b_ok = await b_task

    # Primary invariant: the second concurrent withdrawal must be cap-rejected.
    assert b_ok is False, (
        "second concurrent withdrawal was NOT rejected — the per-user lock did "
        "not serialize the read-then-act cap (BLOCKER B1 regressed)"
    )
    # Corroborating signal: with the lock, B is still blocked when we check;
    # without it, B already finished before A committed.
    assert not b_finished_before_a_committed, (
        "second withdrawal completed before the first committed — advisory lock "
        "was not held across the critical section"
    )

    # Ledger invariant the cap protects: never more outstanding than deposited.
    async with maker() as s:
        amounts = (
            await s.execute(
                select(Withdrawal.amount_uzd).where(Withdrawal.user_id == user_id)
            )
        ).scalars().all()
    assert sum(amounts) <= DEPOSITED


@pytest.mark.asyncio
async def test_concurrent_welcome_claims_drip_once(
    pg: tuple[async_sessionmaker[object], uuid.UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N concurrent welcome claims for one user fire EXACTLY ONE gas drip.

    _ensure_gas reads the live ETH balance then drips if below threshold — a
    check-then-act. The signer releases its per-key lock before the receipt wait
    (B2a), so without a per-user advisory lock a burst of claims all read the
    below-threshold balance and each drip, draining the shared KEY_BANK_OPS ETH
    reserve in one request (blocking review finding).

    Deterministic race (no scheduler-timing reliance): the winner A parks INSIDE
    its drip while still holding the xact-scoped advisory lock; the loser B then
    races. With the lock B blocks on lock_user until A commits, by then reads the
    funded balance and skips (one drip). Without it B reads the stale zero balance
    and drips too (two — the drain this test guards against).
    """
    maker, user_id = pg
    wallet = "0x" + "a" * 40  # the pg-fixture user's wallet

    drip_count = {"n": 0}
    entered = {"n": 0}
    first_parked = asyncio.Event()
    release_first = asyncio.Event()

    async def fake_balance(_wallet: str) -> int:
        # Live chain reflects drips already applied; a fresh wallet reads 0.
        return settings.drip_eth_wei if drip_count["n"] > 0 else 0

    async def fake_send_via(*_args: object, **_kwargs: object) -> str:
        entered["n"] += 1
        if entered["n"] == 1:
            # Winner parks mid-drip, still holding the advisory lock, exposing the
            # below-threshold read window a racing claim would exploit.
            first_parked.set()
            await release_first.wait()
        drip_count["n"] += 1
        return "0x" + "e" * 64

    # Patch at the welcome-service usage site (imported names); monkeypatch
    # auto-restores at teardown.
    monkeypatch.setattr(welcome_service, "get_eth_balance", fake_balance)
    monkeypatch.setattr(welcome_service, "send_via", fake_send_via)

    session_a = maker()

    async def run_a() -> None:
        # Acquires the per-user lock + reads balance=0, then parks in the drip.
        await welcome_service._ensure_gas(session_a, user_id, wallet)

    a_task = asyncio.create_task(run_a())
    await asyncio.wait_for(first_parked.wait(), timeout=5.0)

    async def run_b() -> None:
        async with maker() as s:
            await welcome_service._ensure_gas(s, user_id, wallet)
            await s.commit()

    b_task = asyncio.create_task(run_b())
    # Synchronization point (assertions are deterministic either way): let B
    # reach lock_user. With the lock it blocks; without it it runs to the end.
    await asyncio.sleep(0.5)
    b_finished_before_a_committed = b_task.done()

    release_first.set()  # winner finishes its drip
    await a_task
    await session_a.commit()  # releases the advisory lock
    await session_a.close()
    await asyncio.wait_for(b_task, timeout=5.0)

    assert drip_count["n"] == 1, (
        f"expected exactly one drip under the per-user lock, got {drip_count['n']}"
        " — concurrent welcome claims drained the bank-ops ETH reserve"
    )
    assert not b_finished_before_a_committed, (
        "second claim completed before the first committed — the advisory lock "
        "was not held across the balance-read -> drip critical section"
    )
