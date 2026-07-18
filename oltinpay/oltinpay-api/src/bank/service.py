"""Bank connector service.

A2 idempotency (reserve-then-broadcast, mirroring welcome/service.py exactly):
insert a row with a UNIQUE idempotency key -> flush -> IntegrityError becomes a
409 (no second broadcast) -> broadcast on-chain via the SignerPool -> stamp the
tx_hash. If the broadcast fails AFTER the insert, roll the reservation back so
the bank can retry without an orphan row pinning the idempotency key.

The chain-write helper ``send_via`` is imported here so tests patch it at
``src.bank.service.send_via``.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from src.bank.models import BankDeposit, ReserveAttestation
from src.common.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from src.config import settings
from src.infrastructure import chain_read
from src.infrastructure.signer_pool import (
    Role,
    SignerUnconfigured,
    encode_admin_burn_calldata,
    encode_mint_calldata,
    encode_post_answer_calldata,
    send_via,
)
from src.users import service as user_service
from src.withdrawals import service as withdrawals_service
from src.withdrawals.models import Withdrawal, WithdrawalStatus

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.infrastructure.chain_read import RoundData
    from src.users.models import User

logger = logging.getLogger(__name__)

UZD_DECIMALS = 18
FX_DECIMALS = 8


# --------------------------------------------------------------------------- #
# attestations                                                                #
# --------------------------------------------------------------------------- #
async def post_attestation(
    db: AsyncSession, grams: int, audit_ref: str
) -> ReserveAttestation:
    """Idempotently attest ``grams`` of gold reserve and post it on-chain."""
    row = ReserveAttestation(
        id=uuid.uuid4(), grams=grams, audit_ref=audit_ref, tx_hash=""
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException("auditRef already processed") from exc

    try:
        tx_hash = await send_via(
            Role.RESERVE,
            settings.reserve_attestor_address,
            encode_post_answer_calldata(grams),
        )
    except SignerUnconfigured as exc:
        await db.rollback()
        raise BadRequestException(str(exc)) from exc
    except Exception:
        await db.rollback()
        raise

    row.tx_hash = tx_hash.lower()
    await db.commit()
    await db.refresh(row)
    return row


async def latest_attestation(
    db: AsyncSession,
) -> tuple[ReserveAttestation | None, RoundData]:
    """Latest DB attestation plus the live on-chain reserve reading."""
    result = await db.execute(
        select(ReserveAttestation).order_by(ReserveAttestation.created_at.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    onchain = await chain_read.latest_round_data(settings.reserve_attestor_address)
    return row, onchain


# --------------------------------------------------------------------------- #
# fx                                                                          #
# --------------------------------------------------------------------------- #
async def post_fx(
    uzs_per_usd: float | None, usd_per_uzs: float | None, source: str
) -> tuple[int, str]:
    """Post a UZS/USD rate to the UzsUsdFeed. Returns (answer, tx_hash).

    The feed answer is USD per UZS scaled to 8 decimals — matching the retired
    keeper-uzs (answer = round(1e8 / uzsPerUsd)).
    """
    if uzs_per_usd is not None:
        answer = round(10**FX_DECIMALS / uzs_per_usd)
    elif usd_per_uzs is not None:
        answer = round(usd_per_uzs * 10**FX_DECIMALS)
    else:  # pragma: no cover — guarded by the schema validator
        raise BadRequestException("provide exactly one of uzsPerUsd or usdPerUzs")

    if answer <= 0:
        raise BadRequestException("computed non-positive fx answer")

    try:
        tx_hash = await send_via(
            Role.UZS,
            settings.uzs_feed_address,
            encode_post_answer_calldata(answer),
        )
    except SignerUnconfigured as exc:
        raise BadRequestException(str(exc)) from exc

    logger.info("fx_posted source=%s answer=%s tx=%s", source, answer, tx_hash)
    return answer, tx_hash.lower()


# --------------------------------------------------------------------------- #
# deposits                                                                    #
# --------------------------------------------------------------------------- #
async def _resolve_user(
    db: AsyncSession, user_id: UUID | None, oltin_id: str | None
) -> User | None:
    if user_id is not None:
        return await user_service.get_user_by_id(db, user_id)
    if oltin_id is not None:
        return await user_service.get_user_by_oltin_id(db, oltin_id)
    return None


async def create_deposit(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    oltin_id: str | None,
    amount_uzs: int,
    bank_tx_id: str,
) -> BankDeposit:
    """Idempotently mint UZD for a confirmed fiat deposit."""
    user = await _resolve_user(db, user_id, oltin_id)
    if user is None:
        raise NotFoundException("User not found")
    if not user.wallet_address:
        raise BadRequestException("User has no wallet address")

    amount_wei = amount_uzs * 10**UZD_DECIMALS
    row = BankDeposit(
        id=uuid.uuid4(),
        user_id=user.id,
        bank_tx_id=bank_tx_id,
        amount_uzs=amount_uzs,
        amount_wei=str(amount_wei),
        tx_hash="",
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException("bankTxId already processed") from exc

    try:
        tx_hash = await send_via(
            Role.BANK_OPS,
            settings.uzd_contract_address,
            encode_mint_calldata(user.wallet_address, amount_wei),
        )
    except SignerUnconfigured as exc:
        await db.rollback()
        raise BadRequestException(str(exc)) from exc
    except Exception:
        await db.rollback()
        raise

    row.tx_hash = tx_hash.lower()
    await db.commit()
    await db.refresh(row)
    return row


# --------------------------------------------------------------------------- #
# withdrawals (bank side — confirm burns, reject releases)                     #
# --------------------------------------------------------------------------- #
async def confirm_withdrawal(db: AsyncSession, withdrawal_id: UUID) -> Withdrawal:
    """Burn the user's UZD on-chain and mark the withdrawal confirmed.

    Two-phase, no double-burn: the ``pending -> confirmed`` flip is a guarded
    UPDATE (rowcount==0 => someone else already processed it). The burn happens
    only after the flip is reserved; a failed burn rolls the flip back.

    SECURITY: before burning, a deposit-backed solvency guard refuses to destroy
    more UZD than OltinPay has minted to this user (see below and the
    ``withdrawals.service`` module docstring) so a burn can never reach a third
    party's tokens through an unverified wallet binding.
    """
    withdrawal = await withdrawals_service.get_withdrawal(db, withdrawal_id)
    if withdrawal is None:
        raise NotFoundException("Withdrawal not found")
    if withdrawal.status != WithdrawalStatus.PENDING.value:
        raise ConflictException("Withdrawal is not pending")

    user = withdrawal.user
    if user is None or not user.wallet_address:
        raise BadRequestException("Withdrawal user has no wallet address")
    holder = user.wallet_address
    user_id = withdrawal.user_id
    amount_wei = int(withdrawal.amount_wei)

    # Atomic claim: only one caller can move pending -> confirmed. RETURNING gives
    # a typed "did I win the claim?" signal (works on Postgres and SQLite 3.35+).
    claimed = (
        await db.execute(
            update(Withdrawal)
            .where(
                Withdrawal.id == withdrawal_id,
                Withdrawal.status == WithdrawalStatus.PENDING.value,
            )
            .values(status=WithdrawalStatus.CONFIRMED.value, confirmed_at=func.now())
            .returning(Withdrawal.id)
        )
    ).scalar_one_or_none()
    if claimed is None:
        raise ConflictException("Withdrawal already processed")

    # SECURITY — deposit-backed solvency guard (blocking review finding).
    # adminBurn destroys ANY holder's balance unconditionally, and the burn
    # target (user.wallet_address) is bound with no proof of ownership, so an
    # unchecked burn could destroy a third party's UZD. Refuse to burn more than
    # OltinPay has minted to this user via bank deposits. The pending->confirmed
    # flip above is already applied, so summing CONFIRMED withdrawals includes
    # THIS one; if that total exceeds the user's net deposits, roll the flip back
    # and refuse (no burn). This is the authoritative check — confirms are
    # serialized behind the single KEY_BANK_OPS writer, so the read-then-burn is
    # race-free under the deploy invariant. Amounts are compared in whole-token
    # units (deposit amount_uzs is 1:1 with minted UZD; withdrawal amount_uzd is
    # burned UZD) to avoid summing wei strings.
    deposited = (
        await db.execute(
            select(func.coalesce(func.sum(BankDeposit.amount_uzs), 0)).where(
                BankDeposit.user_id == user_id
            )
        )
    ).scalar_one()
    burned = (
        await db.execute(
            select(func.coalesce(func.sum(Withdrawal.amount_uzd), 0)).where(
                Withdrawal.user_id == user_id,
                Withdrawal.status == WithdrawalStatus.CONFIRMED.value,
            )
        )
    ).scalar_one()
    if int(burned) > int(deposited):
        await db.rollback()
        raise BadRequestException(
            "Withdrawal exceeds the user's net deposited balance; refusing to "
            "burn un-deposited funds."
        )

    try:
        tx_hash = await send_via(
            Role.BANK_OPS,
            settings.uzd_contract_address,
            encode_admin_burn_calldata(holder, amount_wei),
        )
    except SignerUnconfigured as exc:
        await db.rollback()
        raise BadRequestException(str(exc)) from exc
    except Exception:
        await db.rollback()
        raise

    # Stamp the tx hash (ORM), commit, then refresh ONLY the columns the Core
    # UPDATE changed. A full refresh() would expire the eagerly-loaded `user`
    # relationship and trigger an async lazy-load when the response reads it.
    withdrawal.tx_hash = tx_hash.lower()
    await db.commit()
    await db.refresh(withdrawal, attribute_names=["status", "confirmed_at", "tx_hash"])
    return withdrawal


async def reject_withdrawal(db: AsyncSession, withdrawal_id: UUID) -> Withdrawal:
    """Release a pending withdrawal (no on-chain effect)."""
    withdrawal = await withdrawals_service.get_withdrawal(db, withdrawal_id)
    if withdrawal is None:
        raise NotFoundException("Withdrawal not found")
    if withdrawal.status != WithdrawalStatus.PENDING.value:
        raise ConflictException("Withdrawal is not pending")

    claimed = (
        await db.execute(
            update(Withdrawal)
            .where(
                Withdrawal.id == withdrawal_id,
                Withdrawal.status == WithdrawalStatus.PENDING.value,
            )
            .values(status=WithdrawalStatus.REJECTED.value)
            .returning(Withdrawal.id)
        )
    ).scalar_one_or_none()
    if claimed is None:
        raise ConflictException("Withdrawal already processed")

    await db.commit()
    # Refresh only the changed column to keep the loaded `user` relationship.
    await db.refresh(withdrawal, attribute_names=["status"])
    return withdrawal
