"""Users router."""

from fastapi import APIRouter, Query

from src.auth.dependencies import CurrentUser, DbSession
from src.common.exceptions import ConflictException
from src.users import service
from src.users.schemas import (
    OltinIdCreate,
    UserResponse,
    UserSearchResult,
    UserUpdate,
    WalletRegister,
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user info."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Update current user (language only)."""
    user = await service.update_user(db, current_user, update_data)
    return UserResponse.model_validate(user)


@router.post("/oltin-id", response_model=UserResponse)
async def set_oltin_id(
    data: OltinIdCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Set oltin_id for current user.

    Can only be set once. Cannot be changed later.
    """
    # Check if user already has a custom oltin_id (not temp)
    if not current_user.oltin_id.startswith("user_"):
        raise ConflictException("oltin_id already set and cannot be changed")

    # Check if oltin_id is available
    if not await service.check_oltin_id_available(db, data.oltin_id):
        raise ConflictException(f"oltin_id @{data.oltin_id} is already taken")

    user = await service.set_oltin_id(db, current_user, data)
    return UserResponse.model_validate(user)


@router.get("/search", response_model=list[UserSearchResult])
async def search_users(
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=32),
) -> list[UserSearchResult]:
    """Search users by oltin_id prefix."""
    users = await service.search_users(db, q)
    return [UserSearchResult.model_validate(u) for u in users]


@router.post("/wallet", response_model=UserResponse)
async def register_wallet(
    data: WalletRegister,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Attach a non-custodial wallet address to the current user.

    Called once at the end of the client-side onboarding wizard. The
    address is derived from a BIP39 seed that lives on the user's device
    only; the backend never sees the seed or private key.

    Conflict rules:
    - The user can only bind one wallet (first call wins).
    - Another user cannot claim the same address.
    """
    normalized = data.wallet_address.lower()

    if current_user.wallet_address is not None:
        if current_user.wallet_address == normalized:
            return UserResponse.model_validate(current_user)
        raise ConflictException("wallet_address already bound and cannot be changed")

    existing = await service.get_user_by_wallet_address(db, normalized)
    if existing is not None and existing.id != current_user.id:
        raise ConflictException("wallet_address is already bound to another user")

    updated = await service.set_wallet_address(db, current_user, normalized)
    return UserResponse.model_validate(updated)
