"""Users API router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.users.schemas import (
    UpdateUserRequest,
    UserBalanceResponse,
    UserResponse,
    UserSearchResponse,
    UserWithBalancesResponse,
)
from app.database import get_session
from app.infrastructure.models import User
from app.infrastructure.repositories.user_repo import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser):
    """Get current user profile."""
    return UserResponse(
        id=str(user.id),
        phone=user.phone,
        wallet_address=user.wallet_address,
        kyc_level=user.kyc_level,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/me/balances", response_model=UserWithBalancesResponse)
async def get_me_with_balances(user: CurrentUser):
    """Get current user profile with balances."""
    balances = [
        UserBalanceResponse(
            asset=b.asset,
            available=str(b.available),
            locked=str(b.locked),
        )
        for b in user.balances
    ]

    return UserWithBalancesResponse(
        id=str(user.id),
        phone=user.phone,
        wallet_address=user.wallet_address,
        kyc_level=user.kyc_level,
        is_active=user.is_active,
        created_at=user.created_at,
        balances=balances,
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UpdateUserRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """Update current user profile."""
    repo = UserRepository(session)

    if data.wallet_address is not None:
        user.wallet_address = data.wallet_address

    user = await repo.update(user)

    return UserResponse(
        id=str(user.id),
        phone=user.phone,
        wallet_address=user.wallet_address,
        kyc_level=user.kyc_level,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/search", response_model=UserSearchResponse)
async def search_user(
    username: str = Query(..., min_length=1, max_length=32, description="Telegram @username"),
    session: AsyncSession = Depends(get_session),
):
    """
    Search user by Telegram username for internal transfer.

    Returns public info to display before transfer confirmation.
    No authentication required - self-transfer check is done in transfer endpoint.
    """
    from sqlalchemy import select

    # Clean username (remove @ if present)
    clean_username = username.lstrip("@").lower()

    # Search by telegram_username (case-insensitive)
    result = await session.execute(
        select(User).where(func.lower(User.telegram_username) == clean_username)
    )
    found_user = result.scalar_one_or_none()

    if not found_user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserSearchResponse(
        id=str(found_user.id),
        username=found_user.telegram_username,
        first_name=found_user.telegram_first_name,
        has_wallet=bool(found_user.wallet_address),
    )
