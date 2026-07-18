"""Bank connector router — /api/v1/bank/* (HMAC-authenticated).

Every route is guarded by ``require_bank_auth`` (declared on the router).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID  # noqa: TC003 — FastAPI needs the runtime type for path params

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import (
    DbSession,  # noqa: TC001 — FastAPI Depends needs runtime
)
from src.bank import service
from src.bank.deps import require_bank_auth
from src.bank.schemas import (
    AttestationRequest,
    AttestationResponse,
    BankWithdrawalResponse,
    DepositRequest,
    DepositResponse,
    FxRequest,
    FxResponse,
    LatestAttestationResponse,
)
from src.bank.service import FX_DECIMALS
from src.withdrawals import service as withdrawals_service
from src.withdrawals.models import (  # noqa: TC001 — FastAPI query param needs runtime
    WithdrawalStatus,
)

router = APIRouter(dependencies=[Depends(require_bank_auth)])


@router.post("/attestations", response_model=AttestationResponse)
async def post_attestation(
    body: AttestationRequest, db: DbSession
) -> AttestationResponse:
    """Idempotently attest gold reserve and post it to ReserveAttestor."""
    row = await service.post_attestation(db, body.grams, body.audit_ref)
    return AttestationResponse.model_validate(row)


@router.get("/attestations/latest", response_model=LatestAttestationResponse)
async def latest_attestation(db: DbSession) -> LatestAttestationResponse:
    """Latest DB attestation + live on-chain ReserveAttestor reading."""
    row, onchain = await service.latest_attestation(db)
    return LatestAttestationResponse(
        latest=AttestationResponse.model_validate(row) if row is not None else None,
        onchain_answer=str(onchain.answer),
        onchain_updated_at=onchain.updated_at,
        onchain_round_id=onchain.round_id,
    )


@router.post("/fx", response_model=FxResponse)
async def post_fx(body: FxRequest) -> FxResponse:
    """Post a UZS/USD rate to the UzsUsdFeed (KEY_UZS)."""
    answer, tx_hash = await service.post_fx(
        body.uzs_per_usd, body.usd_per_uzs, body.source
    )
    return FxResponse(
        answer=str(answer),
        decimals=FX_DECIMALS,
        source=body.source,
        tx_hash=tx_hash,
    )


@router.post("/deposits", response_model=DepositResponse)
async def create_deposit(body: DepositRequest, db: DbSession) -> DepositResponse:
    """Idempotently mint UZD for a confirmed fiat deposit (KEY_BANK_OPS)."""
    row = await service.create_deposit(
        db,
        user_id=body.user_id,
        oltin_id=body.oltin_id,
        amount_uzs=body.amount_uzs,
        bank_tx_id=body.bank_tx_id,
    )
    return DepositResponse.model_validate(row)


@router.get("/withdrawals", response_model=list[BankWithdrawalResponse])
async def list_withdrawals(
    db: DbSession,
    status: Annotated[WithdrawalStatus | None, Query()] = None,
) -> list[BankWithdrawalResponse]:
    """The withdrawal queue (filter by ``status``, e.g. ?status=pending)."""
    rows = await withdrawals_service.list_withdrawals(db, status)
    return [BankWithdrawalResponse.from_withdrawal(row) for row in rows]


@router.post("/withdrawals/{withdrawal_id}/confirm", response_model=BankWithdrawalResponse)
async def confirm_withdrawal(
    withdrawal_id: UUID, db: DbSession
) -> BankWithdrawalResponse:
    """Bank paid fiat -> burn the user's UZD on-chain (KEY_BANK_OPS)."""
    row = await service.confirm_withdrawal(db, withdrawal_id)
    return BankWithdrawalResponse.from_withdrawal(row)


@router.post("/withdrawals/{withdrawal_id}/reject", response_model=BankWithdrawalResponse)
async def reject_withdrawal(
    withdrawal_id: UUID, db: DbSession
) -> BankWithdrawalResponse:
    """Release a pending withdrawal (no on-chain effect)."""
    row = await service.reject_withdrawal(db, withdrawal_id)
    return BankWithdrawalResponse.from_withdrawal(row)
