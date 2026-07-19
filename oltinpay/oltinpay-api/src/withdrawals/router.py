"""Withdrawals router — user side (POST create, GET own list)."""

from __future__ import annotations

from fastapi import APIRouter

from src.auth.dependencies import (
    CurrentUser,  # noqa: TC001 — FastAPI Depends needs runtime
    DbSession,  # noqa: TC001 — FastAPI Depends needs runtime
)
from src.withdrawals import service
from src.withdrawals.schemas import WithdrawalCreateRequest, WithdrawalResponse

router = APIRouter()


@router.post("", response_model=WithdrawalResponse)
async def create_withdrawal(
    body: WithdrawalCreateRequest, current_user: CurrentUser, db: DbSession
) -> WithdrawalResponse:
    """File a pending withdrawal. The bank burns the UZD on confirm."""
    withdrawal = await service.create_withdrawal(db, current_user, body.amount_uzd)
    return WithdrawalResponse.model_validate(withdrawal)


@router.get("", response_model=list[WithdrawalResponse])
async def list_my_withdrawals(
    current_user: CurrentUser, db: DbSession
) -> list[WithdrawalResponse]:
    """The current user's withdrawals, newest first."""
    rows = await service.get_user_withdrawals(db, current_user.id)
    return [WithdrawalResponse.model_validate(row) for row in rows]
