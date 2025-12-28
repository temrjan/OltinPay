"""Blockchain API router."""

from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app.api.blockchain.schemas import (
    BalanceResponse,
    BurnRequest,
    MintRequest,
    TokenInfoResponse,
    TransactionResponse,
)
from app.domain.exceptions import BlockchainError
from app.infrastructure.blockchain import ZkSyncClient

router = APIRouter(prefix="/blockchain", tags=["blockchain"])


def get_blockchain_client() -> ZkSyncClient:
    """Get blockchain client instance."""
    try:
        return ZkSyncClient()
    except BlockchainError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/token", response_model=TokenInfoResponse)
async def get_token_info():
    """Get OltinToken contract info."""
    client = get_blockchain_client()
    info = await client.get_token_info()
    return TokenInfoResponse(**info)


@router.get("/balance/{address}", response_model=BalanceResponse)
async def get_balance(address: str):
    """Get OLTIN balance for an address."""
    client = get_blockchain_client()
    try:
        balance = await client.get_balance(address)
        return BalanceResponse(address=address, balance=str(balance))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mint", response_model=TransactionResponse)
async def mint_tokens(request: MintRequest):
    """Mint OLTIN tokens (admin only - TODO: add auth)."""
    client = get_blockchain_client()
    try:
        tx_hash = await client.mint(
            to_address=request.to_address,
            grams=Decimal(request.amount_grams),
            order_id=request.order_id,
        )
        return TransactionResponse(tx_hash=tx_hash)
    except BlockchainError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/burn", response_model=TransactionResponse)
async def burn_tokens(request: BurnRequest):
    """Burn OLTIN tokens (admin only - TODO: add auth)."""
    client = get_blockchain_client()
    try:
        tx_hash = await client.burn(
            from_address=request.from_address,
            grams=Decimal(request.amount_grams),
            order_id=request.order_id,
        )
        return TransactionResponse(tx_hash=tx_hash)
    except BlockchainError as e:
        raise HTTPException(status_code=500, detail=str(e))
