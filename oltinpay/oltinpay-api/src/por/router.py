"""Public PoR / rates router + authenticated quote — mounted at /api/v1.

Routes: GET /por, GET /por/history, GET /rates (public, no auth) and GET /quote
(user auth, since it is listed under the user surface in the spec).
"""

from __future__ import annotations

from decimal import Decimal  # noqa: TC003 — FastAPI query param needs runtime
from typing import Annotated

from fastapi import APIRouter, Query

from src.auth.dependencies import (
    CurrentUser,  # noqa: TC001 — FastAPI Depends needs runtime
    DbSession,  # noqa: TC001 — FastAPI Depends needs runtime
)
from src.por import service
from src.por.schemas import (
    PorHistoryItem,
    PorResponse,
    QuoteResponse,
    QuoteSide,
    RatesResponse,
)

router = APIRouter()


@router.get("/por", response_model=PorResponse)
async def get_por() -> PorResponse:
    """Live proof-of-reserve: attested grams, OLTIN supply, coverage, freshness."""
    return await service.get_por()


@router.get("/por/history", response_model=list[PorHistoryItem])
async def get_por_history(db: DbSession) -> list[PorHistoryItem]:
    """Reserve attestations recorded by the indexer (newest first)."""
    return await service.get_por_history(db)


@router.get("/rates", response_model=RatesResponse)
async def get_rates() -> RatesResponse:
    """Live XAU/USD and UZS/USD feeds + derived OLTIN price in UZS."""
    return await service.get_rates()


@router.get("/quote", response_model=QuoteResponse)
async def get_quote(
    current_user: CurrentUser,
    side: Annotated[QuoteSide | None, Query()] = None,
    amount: Annotated[Decimal | None, Query(gt=0)] = None,
) -> QuoteResponse:
    """Buy/sell price preview from the XAU + UZS feeds."""
    _ = current_user  # auth-gated per spec; no per-user data used
    return await service.get_quote(side, amount)
