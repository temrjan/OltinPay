"""Wallet API endpoints."""

from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.api.wallet.schemas import (
    BalanceItem,
    DepositRequest,
    DepositResponse,
    SyncStatusResponse,
    TransactionListResponse,
    TransactionResponse,
    TransferByPhoneRequest,
    TransferRequest,
    TransferResponse,
    WalletBalanceResponse,
)
from app.application.services.wallet_service import WalletService
from app.domain.exceptions import BlockchainError
from app.infrastructure.blockchain.zksync_client import ZkSyncClient
from app.infrastructure.models import User

router = APIRouter(prefix="/wallet", tags=["wallet"])


def get_wallet_service(session: AsyncSession = Depends(get_session)) -> WalletService:
    return WalletService(session)


def get_blockchain() -> ZkSyncClient:
    return ZkSyncClient()


@router.get("/balance", response_model=WalletBalanceResponse)
async def get_balance(
    user: User = Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
):
    """Get current user wallet balances."""
    balances = await service.get_balances(cast(UUID, user.id))

    usd = balances.get("USD", {"available": 0, "locked": 0})
    oltin = balances.get("OLTIN", {"available": 0, "locked": 0})

    return WalletBalanceResponse(
        usd=BalanceItem(
            available=usd["available"],
            locked=usd["locked"],
            total=usd["available"] + usd["locked"],
        ),
        oltin=BalanceItem(
            available=oltin["available"],
            locked=oltin["locked"],
            total=oltin["available"] + oltin["locked"],
        ),
        wallet_address=user.wallet_address,
    )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
):
    """Get transaction history (orders + transfers)."""
    history = await service.get_all_history(
        user_id=cast(UUID, user.id),
        limit=limit,
        offset=offset,
    )

    transactions = [
        TransactionResponse(
            id=str(row["id"]),
            type=row["type"],
            asset=row["asset"] or "OLTIN",
            amount=row["amount"],
            amount_usd=row["amount_usd"],
            amount_oltin=row["amount_oltin"],
            fee_usd=row["fee_usd"],
            tx_hash=row["tx_hash"],
            to_address=row["to_address"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in history
    ]

    return TransactionListResponse(
        transactions=transactions,
        total=len(transactions),
        limit=limit,
        offset=offset,
    )


@router.get("/sync", response_model=SyncStatusResponse)
async def sync_blockchain(
    user: User = Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
):
    """Check sync status between local and blockchain balance."""
    if not user.wallet_address:
        raise HTTPException(
            status_code=400,
            detail="No wallet address configured for user",
        )

    result = await service.sync_blockchain_balance(
        user_id=cast(UUID, user.id),
        wallet_address=user.wallet_address,
    )

    return SyncStatusResponse(**result)


@router.post("/deposit", response_model=DepositResponse)
async def deposit_uzs(
    request: DepositRequest,
    user: User = Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
):
    """Deposit USD to wallet (for testing/demo mode)."""
    if request.amount_usd <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be positive",
        )

    result = await service.deposit_uzs(cast(UUID, user.id), request.amount_usd)
    return DepositResponse(**result)


@router.post("/transfer", response_model=TransferResponse)
async def transfer_oltin(
    request: TransferRequest,
    user: User = Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
    session: AsyncSession = Depends(get_session),
    blockchain: ZkSyncClient = Depends(get_blockchain),
):
    """Transfer OLTIN to another wallet address (gasless via adminTransfer)."""
    if not user.wallet_address:
        raise HTTPException(
            status_code=400,
            detail="User wallet not configured",
        )

    # Check balance
    balances = await service.get_balances(cast(UUID, user.id))
    oltin_balance = balances.get("OLTIN", {"available": 0})

    if oltin_balance["available"] < request.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient OLTIN balance. Available: {oltin_balance['available']}",
        )

    transfer_id = f"tf-{str(uuid4())[:8]}"

    try:
        tx_hash, net_amount, fee_amount = await blockchain.admin_transfer(
            from_address=user.wallet_address,
            to_address=request.to_address,
            grams=request.amount,
            transfer_id=transfer_id,
        )

        # Update sender balance
        await service.update_balance(
            user_id=cast(UUID, user.id),
            asset="OLTIN",
            delta=-request.amount,
        )

        # Update receiver if in system
        result = await session.execute(
            select(User).where(User.wallet_address == request.to_address)
        )
        receiver = result.scalar_one_or_none()
        if receiver:
            await service.update_balance(
                user_id=cast(UUID, receiver.id),
                asset="OLTIN",
                delta=net_amount,
            )

        # Record transaction
        await service.record_transfer(
            user_id=cast(UUID, user.id),
            to_address=request.to_address,
            amount=request.amount,
            tx_hash=tx_hash,
        )

        return TransferResponse(
            success=True,
            tx_hash=tx_hash,
            from_address=user.wallet_address,
            to_address=request.to_address,
            amount=request.amount,
            net_amount=net_amount,
            fee_amount=fee_amount,
            message=f"Transferred {net_amount} OLTIN (fee: {fee_amount})",
        )

    except BlockchainError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Blockchain error: {str(e)}",
        )


@router.post("/transfer-by-phone", response_model=TransferResponse)
async def transfer_by_phone(
    request: TransferByPhoneRequest,
    user: User = Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
    session: AsyncSession = Depends(get_session),
    blockchain: ZkSyncClient = Depends(get_blockchain),
):
    """Transfer OLTIN to user by phone number (gasless)."""
    if not user.wallet_address:
        raise HTTPException(
            status_code=400,
            detail="User wallet not configured",
        )

    # Find recipient by phone
    result = await session.execute(select(User).where(User.phone == request.phone))
    recipient = result.scalar_one_or_none()

    if not recipient:
        raise HTTPException(
            status_code=404,
            detail=f"User with phone {request.phone} not found",
        )

    if not recipient.wallet_address:
        raise HTTPException(
            status_code=400,
            detail="Recipient has no wallet",
        )

    if recipient.id == user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot transfer to yourself",
        )

    # Check balance
    balances = await service.get_balances(cast(UUID, user.id))
    oltin_balance = balances.get("OLTIN", {"available": 0})

    if oltin_balance["available"] < request.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient OLTIN balance. Available: {oltin_balance['available']}",
        )

    transfer_id = f"tfp-{str(uuid4())[:8]}"

    try:
        tx_hash, net_amount, fee_amount = await blockchain.admin_transfer(
            from_address=user.wallet_address,
            to_address=recipient.wallet_address,
            grams=request.amount,
            transfer_id=transfer_id,
        )

        # Update sender balance
        await service.update_balance(
            user_id=cast(UUID, user.id),
            asset="OLTIN",
            delta=-request.amount,
        )

        # Update receiver balance
        await service.update_balance(
            user_id=cast(UUID, recipient.id),
            asset="OLTIN",
            delta=net_amount,
        )

        # Record transaction
        await service.record_transfer(
            user_id=cast(UUID, user.id),
            to_address=recipient.wallet_address,
            amount=request.amount,
            tx_hash=tx_hash,
        )

        return TransferResponse(
            success=True,
            tx_hash=tx_hash,
            from_address=user.wallet_address,
            to_address=recipient.wallet_address,
            recipient_phone=request.phone,
            amount=request.amount,
            net_amount=net_amount,
            fee_amount=fee_amount,
            message=f"Transferred {net_amount} OLTIN to {request.phone} (fee: {fee_amount})",
        )

    except BlockchainError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Blockchain error: {str(e)}",
        )
