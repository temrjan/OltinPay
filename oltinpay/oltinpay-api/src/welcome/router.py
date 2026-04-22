"""Welcome bonus router — 1000 UZD minted once per user."""

from __future__ import annotations

from fastapi import APIRouter

from src.auth.dependencies import (  # noqa: TC001  — FastAPI Depends needs runtime
    CurrentUser,
    DbSession,
)
from src.welcome import service
from src.welcome.schemas import WelcomeClaimResponse, WelcomeStatusResponse

router = APIRouter()


@router.get("/status", response_model=WelcomeStatusResponse)
async def welcome_status(
    current_user: CurrentUser, db: DbSession
) -> WelcomeStatusResponse:
    """Has the user already claimed the bonus?"""
    claim = await service.get_existing_claim(db, current_user)
    if claim is None:
        return WelcomeStatusResponse(claimed=False)
    return WelcomeStatusResponse(
        claimed=True,
        tx_hash=claim.tx_hash,
        claimed_at=claim.claimed_at,
    )


@router.post("/claim", response_model=WelcomeClaimResponse)
async def claim_welcome(
    current_user: CurrentUser, db: DbSession
) -> WelcomeClaimResponse:
    """Mint 1000 UZD to the user's wallet. Admin-signed, one-time per user."""
    claim = await service.claim_welcome_bonus(db, current_user)
    return WelcomeClaimResponse.model_validate(claim)
