"""User deposit-intent router — POST /api/v1/deposits."""

from __future__ import annotations

from fastapi import APIRouter

from src.auth.dependencies import (
    CurrentUser,  # noqa: TC001 — FastAPI Depends needs runtime
)
from src.deposits import service
from src.deposits.schemas import DepositIntentRequest, DepositIntentResponse

router = APIRouter()


@router.post("", response_model=DepositIntentResponse)
async def create_deposit_intent(
    body: DepositIntentRequest, current_user: CurrentUser
) -> DepositIntentResponse:
    """Return demo bank requisites for funding the account with UZS."""
    return service.create_intent(current_user, body.amount_uzs)
