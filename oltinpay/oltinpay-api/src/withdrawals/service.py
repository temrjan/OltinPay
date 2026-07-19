"""Withdrawal service — user create + shared reads.

The on-chain confirm (UZD burn) and reject transitions live in
``src.bank.service`` because they are bank operations; they mutate this same
table. Keeping them there also keeps the SignerPool send patchable at
``src.bank.service.send_via`` in tests.

SECURITY — deposit-backed solvency cap (blocking review finding):
``UZD.adminBurn(holder, amount)`` unconditionally destroys ``holder``'s balance
(only the caller needs BURNER_ROLE — the holder never signs). A withdrawal's
burn target is ``user.wallet_address``, which is bound at ``POST /users/wallet``
with no proof of ownership. Without a cap, an attacker could bind a third
party's UZD-holding address as their wallet, file a withdrawal, and have the
bank burn that third party's tokens. We therefore bound every user's cumulative
withdrawals by their cumulative confirmed bank deposits: a burn can only ever
destroy UZD OltinPay itself minted to that user, never external/third-party
funds. The authoritative, single-writer-serialized backstop lives in
``bank/service.confirm_withdrawal`` (it gates the actual burn); the check here
is the fast, at-file-time guard that keeps the bank queue clean.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.bank.models import BankDeposit
from src.common.exceptions import BadRequestException
from src.infrastructure.db_lock import lock_user
from src.withdrawals.models import Withdrawal, WithdrawalStatus

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.users.models import User

UZD_DECIMALS = 18


async def available_to_withdraw(db: AsyncSession, user_id: UUID) -> int:
    """Net UZD the user may still withdraw = deposited minus outstanding.

    ``deposited`` is the sum of the user's confirmed bank-deposit amounts (each
    UZS deposit mints an equal number of UZD, 1:1). ``outstanding`` is the sum
    of the user's pending + confirmed + reconcile withdrawals (each will burn,
    has burned, or MAY have burned that many UZD — a RECONCILE burn's outcome is
    unknown and is counted conservatively as having happened; see the
    ``withdrawals.models`` RECONCILE invariant). The difference is the
    OltinPay-minted UZD not yet spoken for by a withdrawal. Comparison is done
    in whole-token units on the ``BigInteger`` columns (``amount_uzs`` /
    ``amount_uzd``) — never on the wei strings, which overflow SQLite's 64-bit
    integers.
    """
    deposited = (
        await db.execute(
            select(func.coalesce(func.sum(BankDeposit.amount_uzs), 0)).where(
                BankDeposit.user_id == user_id
            )
        )
    ).scalar_one()
    outstanding = (
        await db.execute(
            select(func.coalesce(func.sum(Withdrawal.amount_uzd), 0)).where(
                Withdrawal.user_id == user_id,
                Withdrawal.status.in_(
                    [
                        WithdrawalStatus.PENDING.value,
                        WithdrawalStatus.CONFIRMED.value,
                        # Maybe-burned (unknown outcome) — counted conservatively
                        # so a parked burn can't free up cap for another one.
                        WithdrawalStatus.RECONCILE.value,
                    ]
                ),
            )
        )
    ).scalar_one()
    return int(deposited) - int(outstanding)


async def create_withdrawal(
    db: AsyncSession, user: User, amount_uzd: int
) -> Withdrawal:
    """File a pending withdrawal for ``amount_uzd`` UZD.

    No on-chain effect — the UZD is burned only when the bank confirms. The
    amount is capped at the user's deposit-backed balance (see module docstring
    SECURITY note); the authoritative re-check happens at bank confirm.
    """
    if not user.wallet_address:
        raise BadRequestException(
            "Wallet address not registered. Complete onboarding first."
        )
    if amount_uzd <= 0:
        raise BadRequestException("amount_uzd must be positive")

    # Serialize this user's create/confirm ops (BLOCKER B1): the deposit-backed
    # cap below sums-then-acts, so without a per-user lock two concurrent creates
    # could both pass under Postgres READ COMMITTED. Held until this request's
    # transaction commits/rolls back. No-op on SQLite (see db_lock.lock_user).
    await lock_user(db, user.id)
    available = await available_to_withdraw(db, user.id)
    if amount_uzd > available:
        raise BadRequestException(
            f"Withdrawal exceeds your available balance ({available} UZD). You "
            "can withdraw at most the net UZD deposited to your wallet through "
            "OltinPay."
        )

    withdrawal = Withdrawal(
        id=uuid.uuid4(),
        user_id=user.id,
        amount_uzd=amount_uzd,
        amount_wei=str(amount_uzd * 10**UZD_DECIMALS),
        status=WithdrawalStatus.PENDING.value,
    )
    db.add(withdrawal)
    await db.flush()
    await db.refresh(withdrawal)
    return withdrawal


async def get_withdrawal(db: AsyncSession, withdrawal_id: UUID) -> Withdrawal | None:
    """Load a withdrawal with its user eagerly attached."""
    result = await db.execute(
        select(Withdrawal)
        .options(selectinload(Withdrawal.user))
        .where(Withdrawal.id == withdrawal_id)
    )
    return result.scalar_one_or_none()


async def list_withdrawals(
    db: AsyncSession,
    status: WithdrawalStatus | None = None,
    limit: int = 100,
) -> list[Withdrawal]:
    """List withdrawals (optionally filtered by status), newest first."""
    query = select(Withdrawal).options(selectinload(Withdrawal.user))
    if status is not None:
        query = query.where(Withdrawal.status == status.value)
    query = query.order_by(Withdrawal.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_withdrawals(
    db: AsyncSession, user_id: UUID, limit: int = 50
) -> list[Withdrawal]:
    """List a single user's withdrawals, newest first."""
    result = await db.execute(
        select(Withdrawal)
        .where(Withdrawal.user_id == user_id)
        .order_by(Withdrawal.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
