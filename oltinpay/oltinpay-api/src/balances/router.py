"""Balances router."""

from fastapi import APIRouter

from src.auth.dependencies import CurrentUser, DbSession
from src.balances import service
from src.balances.schemas import (
    BalancesResponse,
    InternalTransferRequest,
    InternalTransferResponse,
)

router = APIRouter()


@router.get("", response_model=BalancesResponse)
async def get_balances(
    current_user: CurrentUser,
    db: DbSession,
) -> BalancesResponse:
    """Get all user balances."""
    return await service.get_user_balances(db, current_user.id)


@router.post("/transfer", response_model=InternalTransferResponse)
async def internal_transfer(
    request: InternalTransferRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> InternalTransferResponse:
    """Transfer between own accounts (free)."""
    await service.internal_transfer(
        db,
        user_id=current_user.id,
        from_account=request.from_account,
        to_account=request.to_account,
        currency=request.currency,
        amount=request.amount,
    )

    return InternalTransferResponse(
        from_account=request.from_account,
        to_account=request.to_account,
        currency=request.currency,
        amount=request.amount,
    )
