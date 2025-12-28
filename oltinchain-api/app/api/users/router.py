"""Users API router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.users.schemas import (
    UpdateUserRequest,
    UserBalanceResponse,
    UserResponse,
    UserWithBalancesResponse,
)
from app.database import get_session
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
