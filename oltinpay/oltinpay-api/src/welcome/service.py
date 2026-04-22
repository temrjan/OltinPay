"""Welcome bonus service — DEMO 1000 UZD mint per user."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.common.exceptions import BadRequestException, ConflictException
from src.config import settings
from src.infrastructure.admin_tx import AdminUnconfigured, send_admin_mint
from src.welcome.models import WelcomeClaim

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.users.models import User

BONUS_AMOUNT_WEI = 1000 * 10**18  # 1000 UZD with 18 decimals


async def get_existing_claim(
    db: AsyncSession, user: User
) -> WelcomeClaim | None:
    result = await db.execute(
        select(WelcomeClaim).where(WelcomeClaim.user_id == user.id)
    )
    return result.scalar_one_or_none()


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

    # Step 2 — broadcast. On failure, rollback the reservation so the
    # user can retry without an orphan row pinning the unique slot.
    try:
        tx_hash = await send_admin_mint(
            contract=settings.uzd_contract_address,
            recipient=wallet,
            amount_wei=BONUS_AMOUNT_WEI,
        )
    except AdminUnconfigured as exc:
        await db.rollback()
        raise BadRequestException(str(exc)) from exc
    except Exception:
        await db.rollback()
        raise

    claim.tx_hash = tx_hash.lower()
    await db.commit()
    return claim
