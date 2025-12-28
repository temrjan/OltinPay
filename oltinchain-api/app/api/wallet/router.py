"""Wallet API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.api.wallet.schemas import (
    DepositRequest,
    DepositResponse,
    WalletBalanceResponse,
    BalanceItem,
    TransactionResponse,
    TransactionListResponse,
    SyncStatusResponse,
    TransferRequest,
    TransferResponse,
)
from app.application.services.wallet_service import WalletService
from app.infrastructure.blockchain.zksync_client import ZkSyncClient
from app.infrastructure.repositories.user_repo import decrypt_private_key
from app.infrastructure.models import User
from app.domain.exceptions import BlockchainError

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
    balances = await service.get_balances(user.id)

    uzs = balances.get("UZS", {"available": 0, "locked": 0})
    oltin = balances.get("OLTIN", {"available": 0, "locked": 0})

    return WalletBalanceResponse(
        uzs=BalanceItem(
            available=uzs["available"],
            locked=uzs["locked"],
            total=uzs["available"] + uzs["locked"],
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
    """Get transaction history from completed orders."""
    orders = await service.get_transactions_from_orders(
        user_id=user.id,
        limit=limit,
        offset=offset,
    )

    transactions = [
        TransactionResponse(
            id=str(order.id),
            type=order.type,
            asset="OLTIN" if order.type == "buy" else "UZS",
            amount=order.amount_oltin if order.type == "buy" else order.amount_uzs,
            amount_uzs=order.amount_uzs,
            amount_oltin=order.amount_oltin,
            fee_uzs=order.fee_uzs,
            tx_hash=order.tx_hash,
            status=order.status,
            created_at=order.created_at,
        )
        for order in orders
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
        user_id=user.id,
        wallet_address=user.wallet_address,
    )

    return SyncStatusResponse(**result)


@router.post("/deposit", response_model=DepositResponse)
async def deposit_uzs(
    request: DepositRequest,
    user: User = Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
):
    """Deposit UZS to wallet (for testing/demo mode)."""
    if request.amount_uzs <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be positive",
        )
    
    result = await service.deposit_uzs(user.id, request.amount_uzs)
    return DepositResponse(**result)


@router.post("/transfer", response_model=TransferResponse)
async def transfer_oltin(
    request: TransferRequest,
    user: User = Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
    blockchain: ZkSyncClient = Depends(get_blockchain),
):
    """Transfer OLTIN to another wallet address (on-chain)."""
    # Check user has wallet
    if not user.wallet_address or not user.encrypted_private_key:
        raise HTTPException(
            status_code=400,
            detail="User wallet not configured",
        )
    
    # Check balance
    balances = await service.get_balances(user.id)
    oltin_balance = balances.get("OLTIN", {"available": 0})
    
    if oltin_balance["available"] < request.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient OLTIN balance. Available: {oltin_balance['available']}",
        )
    
    try:
        # Decrypt private key
        private_key = decrypt_private_key(user.encrypted_private_key)
        
        # Execute on-chain transfer
        tx_hash = await blockchain.transfer(
            from_private_key=private_key,
            to_address=request.to_address,
            grams=request.amount,
        )
        
        # Update local balance (decrease sender)
        await service.update_balance(
            user_id=user.id,
            asset="OLTIN",
            delta=-request.amount,
        )
        
        # Record transaction
        await service.record_transfer(
            user_id=user.id,
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
            message="Transfer completed successfully",
        )
        
    except BlockchainError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Blockchain error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transfer failed: {str(e)}",
        )
