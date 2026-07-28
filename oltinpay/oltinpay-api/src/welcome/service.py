"""Welcome bonus service — DEMO 1000 UZD mint + one-off ETH gas drip per user."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from eth_utils.address import to_checksum_address
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.common.exceptions import BadRequestException, ConflictException
from src.config import settings
from src.infrastructure.db_lock import lock_user
from src.infrastructure.rpc import RpcError, get_eth_balance
from src.infrastructure.signer_pool import (
    Role,
    SignerError,
    SignerReceiptTimeout,
    SignerUnconfigured,
    encode_mint_calldata,
    send_via,
)
from src.welcome.models import WelcomeClaim

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.users.models import User

logger = logging.getLogger(__name__)

BONUS_AMOUNT_WEI = 1000 * 10**18  # 1000 UZD with 18 decimals


async def get_existing_claim(
    db: AsyncSession, user: User
) -> WelcomeClaim | None:
    result = await db.execute(
        select(WelcomeClaim).where(WelcomeClaim.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def _ensure_gas(db: AsyncSession, user_id: uuid.UUID, wallet: str) -> None:
    """Best-effort, idempotent native ETH drip so a fresh wallet can pay its
    first plain-tx.

    zkSync AA charges the paymaster fee in OLTIN, which a brand-new wallet has
    zero of, so its FIRST on-chain action (an approve/buy) must be a plain,
    ETH-paid tx. Welcome mints only UZD, so without a one-off ETH drip the wallet
    could never sign that first tx.

    Idempotency comes from the LIVE chain balance (source of truth), not a DB
    flag: the drip fires only when the wallet is below the threshold, so a retry
    after a transient failure never double-drips. Best-effort — a drip failure
    must NOT abort the UZD claim (the mint is the bonus; gas is a convenience).
    Because ``claim_welcome_bonus`` calls this BEFORE the one-time reservation,
    re-calling claim tops the wallet up even once the claim itself returns 409.

    CONCURRENCY (blocking review finding): the balance read → drip is a check-
    then-act on live chain state. The signer's per-key lock is released before the
    receipt wait (B2a), so N parallel claims for one user would ALL read a below-
    threshold balance and each fire a drip — a one-request drain of the shared
    KEY_BANK_OPS ETH reserve, not a mere double-click. A transaction-scoped per-
    user advisory lock (same pattern as withdrawals/bank, no-op on SQLite) makes
    the check-then-act one-at-a-time per user: the loser blocks until the winner's
    transaction commits, by then reads the funded balance, and skips.
    """
    await lock_user(db, user_id)
    try:
        balance = await get_eth_balance(wallet)
    except RpcError:
        # Could not confirm the balance — skip this round rather than risk an
        # unguarded (non-idempotent) drip; a later call retries.
        logger.warning(
            "welcome_gas_balance_read_failed wallet=%s", wallet, exc_info=True
        )
        return

    if balance >= settings.drip_eth_threshold_wei:
        return  # already funded — the chain says so

    try:
        # eth_account requires a checksummed `to`; the wallet is stored lower-
        # cased, so checksum it here (the mint path never hits this — there the
        # recipient rides in the calldata and `to` is the checksummed contract).
        await send_via(
            Role.BANK_OPS,
            to_checksum_address(wallet),
            "0x",
            value=settings.drip_eth_wei,
        )
    except (SignerError, SignerUnconfigured):
        # KEY_BANK_OPS may be out of ETH (a predictable operational condition) or
        # the drip may time out. Never fail the claim — the balance-gated retry on
        # a later call tops the wallet up once bank-ops is refunded.
        logger.warning("welcome_gas_drip_failed wallet=%s", wallet, exc_info=True)


async def claim_welcome_bonus(db: AsyncSession, user: User) -> WelcomeClaim:
    """Mint 1000 UZD to the user's wallet. One call per user ever.

    Reserve-then-broadcast pattern — the DB row with a unique constraint on
    user_id is inserted FIRST and committed, so concurrent claims fail fast
    on the unique-constraint violation instead of double-minting. Only after
    the slot is reserved do we broadcast the on-chain mint, then update the
    same row with the resulting tx_hash.
    """
    if not user.wallet_address:
        raise BadRequestException(
            "Wallet address not registered. Complete onboarding first."
        )

    wallet = user.wallet_address.lower()

    # Fund the wallet's first plain-tx BEFORE reserving the one-time UZD slot, so
    # a user whose earlier drip failed can re-call claim and still get topped up
    # even though the reservation then returns 409. Best-effort — never blocks the
    # mint (see _ensure_gas). The per-user advisory lock taken inside serializes
    # concurrent claims so a burst cannot drain the bank-ops ETH reserve.
    await _ensure_gas(db, user.id, wallet)

    # Step 1 — reserve the unique slot inside the open transaction. The
    # unique index on user_id makes a concurrent second flush block until
    # our tx resolves and then fail fast with IntegrityError, so only one
    # call ever reaches step 2.
    claim = WelcomeClaim(
        # Generate PK client-side so the in-memory object is identifiable
        # after flush regardless of RETURNING support in the driver.
        id=uuid.uuid4(),
        user_id=user.id,
        wallet_address=wallet,
        tx_hash="",  # placeholder, filled after broadcast
        amount_wei=str(BONUS_AMOUNT_WEI),
    )
    db.add(claim)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException("Welcome bonus already claimed") from exc

    # Step 2 — broadcast via the KEY_BANK_OPS signer (the sole UZD minter, so
    # the welcome mint shares one serialized nonce stream with bank deposits).
    # On failure, rollback the reservation so the user can retry without an
    # orphan row pinning the unique slot.
    try:
        tx_hash = await send_via(
            Role.BANK_OPS,
            settings.uzd_contract_address,
            encode_mint_calldata(wallet, BONUS_AMOUNT_WEI),
        )
    except SignerUnconfigured as exc:
        await db.rollback()
        raise BadRequestException(str(exc)) from exc
    except SignerReceiptTimeout as exc:
        # A-prime (mint-symmetry): outcome UNKNOWN — keep the reserved slot so a
        # retry can't mint a SECOND welcome bonus if the timed-out tx later
        # mines. The user_id unique slot stays claimed; a retry gets 409. Same
        # keep-reservation contract as bank.create_deposit.
        claim.tx_hash = exc.tx_hash.lower()
        await db.commit()
        raise ConflictException(
            "Mint outcome unknown (no receipt within the timeout); welcome "
            "bonus reserved for reconciliation. Do not retry."
        ) from exc
    except Exception:
        await db.rollback()
        raise

    claim.tx_hash = tx_hash.lower()
    await db.commit()
    return claim
