"""Staking router."""

from fastapi import APIRouter

from src.auth.dependencies import CurrentUser, DbSession
from src.staking import service
from src.staking.schemas import (
    StakingDepositRequest,
    StakingDepositResponse,
    StakingInfoResponse,
    StakingRewardResponse,
    StakingWithdrawRequest,
    StakingWithdrawResponse,
)

router = APIRouter()


@router.get("", response_model=StakingInfoResponse)
async def get_staking_info(
    current_user: CurrentUser,
    db: DbSession,
) -> StakingInfoResponse:
    """Get staking info.

    Returns balance, lock status, APY, daily reward, total earned.
    """
    return await service.get_staking_info(db, current_user.id)


@router.post("/deposit", response_model=StakingDepositResponse)
async def deposit_to_staking(
    request: StakingDepositRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> StakingDepositResponse:
    """Deposit OLTIN to staking.

    Moves OLTIN from wallet to staking.
    Resets lock period to 7 days.
    """
    new_balance, locked_until = await service.deposit_to_staking(
        db,
        user_id=current_user.id,
        amount=request.amount,
    )

    return StakingDepositResponse(
        new_balance=new_balance,
        locked_until=locked_until,
    )


@router.post("/withdraw", response_model=StakingWithdrawResponse)
async def withdraw_from_staking(
    request: StakingWithdrawRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> StakingWithdrawResponse:
    """Withdraw OLTIN from staking.

    Fails if still locked.
    """
    withdrawn, remaining = await service.withdraw_from_staking(
        db,
        user_id=current_user.id,
        amount=request.amount,
    )

    return StakingWithdrawResponse(
        withdrawn=withdrawn,
        remaining=remaining,
    )


@router.get("/rewards", response_model=list[StakingRewardResponse])
async def get_staking_rewards(
    current_user: CurrentUser,
    db: DbSession,
) -> list[StakingRewardResponse]:
    """Get staking rewards history."""
    return await service.get_staking_rewards(db, current_user.id)


@router.post("/rewards/calculate")
async def calculate_rewards(
    db: DbSession,
) -> dict:
    """Calculate and credit daily rewards for all stakers.

    Called by cron job. Can be triggered manually for testing.
    Idempotent - safe to call multiple times per day.
    """
    result = await service.calculate_and_credit_rewards(db)
    await db.commit()
    return result
