"""Transactions router — GET /api/v1/transactions (indexer-backed)."""

from __future__ import annotations

from fastapi import APIRouter

from src.auth.dependencies import (
    CurrentUser,  # noqa: TC001 — FastAPI Depends needs runtime
    DbSession,  # noqa: TC001 — FastAPI Depends needs runtime
)
from src.common.exceptions import BadRequestException
from src.indexer import service
from src.indexer.schemas import TransactionItem

router = APIRouter()


@router.get("", response_model=list[TransactionItem])
async def get_transactions(
    current_user: CurrentUser, db: DbSession
) -> list[TransactionItem]:
    """The user's on-chain transaction feed with explorer links."""
    if not current_user.wallet_address:
        raise BadRequestException(
            "Wallet address not registered. Complete onboarding first."
        )
    return await service.get_transactions(db, current_user.wallet_address)
