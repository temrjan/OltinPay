"""Staking service layer."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.balances.models import AccountType, Currency
from src.balances.service import get_balance
from src.common.exceptions import BadRequestException, InsufficientBalanceException
from src.staking.models import StakingDeposit, StakingReward
from src.staking.schemas import StakingInfoResponse, StakingRewardResponse

# Staking constants
APY = Decimal("0.07")  # 7%
LOCK_DAYS = 7
DAILY_RATE = APY / Decimal("365")  # ~0.00019178


async def get_staking_info(db: AsyncSession, user_id: UUID) -> StakingInfoResponse:
    """Get user's staking info."""
    # Get staking balance
    balance = await get_balance(db, user_id, AccountType.STAKING, Currency.OLTIN)
    staking_balance = balance.amount if balance else Decimal("0")

    # Get latest deposit to check lock
    result = await db.execute(
        select(StakingDeposit)
        .where(StakingDeposit.user_id == user_id)
        .order_by(StakingDeposit.unlocked_at.desc())
        .limit(1)
    )
    latest_deposit = result.scalar_one_or_none()

    now = datetime.now(UTC)
    locked_until = None
    is_locked = False

    if latest_deposit and latest_deposit.unlocked_at > now:
        locked_until = latest_deposit.unlocked_at
        is_locked = True

    # Calculate daily reward
    daily_reward = staking_balance * DAILY_RATE

    # Get total earned
    total_result = await db.execute(
        select(func.coalesce(func.sum(StakingReward.amount), 0)).where(
            StakingReward.user_id == user_id
        )
    )
    total_earned = total_result.scalar_one()

    return StakingInfoResponse(
        balance=staking_balance,
        locked_until=locked_until,
        is_locked=is_locked,
        apy=APY,
        daily_reward=daily_reward,
        total_earned=total_earned,
    )


async def deposit_to_staking(
    db: AsyncSession,
    user_id: UUID,
    amount: Decimal,
) -> tuple[Decimal, datetime]:
    """Deposit OLTIN to staking.

    Moves from wallet to staking.
    Resets lock period to 7 days.
    """
    # Get wallet balance
    wallet_balance = await get_balance(db, user_id, AccountType.WALLET, Currency.OLTIN)
    if not wallet_balance or wallet_balance.amount < amount:
        raise InsufficientBalanceException("Insufficient OLTIN in wallet")

    # Get staking balance
    staking_balance = await get_balance(
        db, user_id, AccountType.STAKING, Currency.OLTIN
    )
    if not staking_balance:
        raise BadRequestException("Staking account not found")

    # Transfer
    wallet_balance.amount -= amount
    staking_balance.amount += amount

    # Create deposit record with new lock
    unlocked_at = datetime.now(UTC) + timedelta(days=LOCK_DAYS)
    deposit = StakingDeposit(
        user_id=user_id,
        amount=amount,
        unlocked_at=unlocked_at,
    )
    db.add(deposit)

    await db.flush()

    return staking_balance.amount, unlocked_at


async def withdraw_from_staking(
    db: AsyncSession,
    user_id: UUID,
    amount: Decimal,
) -> tuple[Decimal, Decimal]:
    """Withdraw OLTIN from staking.

    Fails if locked.
    """
    # Check lock status
    info = await get_staking_info(db, user_id)
    if info.is_locked:
        raise BadRequestException(
            f"Staking is locked until {info.locked_until.isoformat() if info.locked_until else "unknown"}"
        )

    # Get staking balance
    staking_balance = await get_balance(
        db, user_id, AccountType.STAKING, Currency.OLTIN
    )
    if not staking_balance or staking_balance.amount < amount:
        raise InsufficientBalanceException("Insufficient OLTIN in staking")

    # Get wallet balance
    wallet_balance = await get_balance(db, user_id, AccountType.WALLET, Currency.OLTIN)
    if not wallet_balance:
        raise BadRequestException("Wallet not found")

    # Transfer
    staking_balance.amount -= amount
    wallet_balance.amount += amount

    await db.flush()

    return amount, staking_balance.amount


async def get_staking_rewards(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 30,
) -> list[StakingRewardResponse]:
    """Get user's staking rewards history."""
    result = await db.execute(
        select(StakingReward)
        .where(StakingReward.user_id == user_id)
        .order_by(StakingReward.reward_date.desc())
        .limit(limit)
    )
    rewards = result.scalars().all()

    return [
        StakingRewardResponse(
            date=r.reward_date,
            amount=r.amount,
            balance_snapshot=r.balance_snapshot,
        )
        for r in rewards
    ]
