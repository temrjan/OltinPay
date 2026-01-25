"""Transfers router."""

from uuid import UUID

from fastapi import APIRouter, Query

from src.auth.dependencies import CurrentUser, DbSession
from src.common.exceptions import NotFoundException
from src.transfers import service
from src.transfers.schemas import (
    TransferDetailResponse,
    TransferListResponse,
    TransferRequest,
    TransferResponse,
)

router = APIRouter()


@router.post("", response_model=TransferResponse)
async def create_transfer(
    request: TransferRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> TransferResponse:
    """Create OLTIN transfer to another user.

    Transfers OLTIN from wallet to recipient's wallet.
    Fee: 1% (min 0.05 USD equivalent).
    """
    transfer = await service.create_transfer(
        db,
        from_user=current_user,
        to_oltin_id=request.to_oltin_id,
        amount=request.amount,
    )

    return TransferResponse(
        id=transfer.id,
        amount=transfer.amount,
        fee=transfer.fee,
        net_amount=transfer.amount - transfer.fee,
        status=transfer.status,
        created_at=transfer.created_at,
    )


@router.get("", response_model=list[TransferListResponse])
async def get_transfers(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[TransferListResponse]:
    """Get user's transfers (sent and received)."""
    transfers = await service.get_user_transfers(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return [service.format_transfer_list_item(t, current_user.id) for t in transfers]


@router.get("/{transfer_id}", response_model=TransferDetailResponse)
async def get_transfer(
    transfer_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> TransferDetailResponse:
    """Get transfer details."""
    transfer = await service.get_transfer_by_id(
        db,
        transfer_id=transfer_id,
        user_id=current_user.id,
    )

    if not transfer:
        raise NotFoundException("Transfer not found")

    return TransferDetailResponse(
        id=transfer.id,
        from_oltin_id=transfer.from_user.oltin_id,
        to_oltin_id=transfer.to_user.oltin_id,
        amount=transfer.amount,
        fee=transfer.fee,
        tx_hash=transfer.tx_hash,
        status=transfer.status,
        created_at=transfer.created_at,
        confirmed_at=transfer.confirmed_at,
    )
