"""Reserves API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.reserves.schemas import (
    ProofOfReservesResponse,
    GoldBarResponse,
    GoldBarListResponse,
)
from app.application.services.reserves_service import ReservesService

router = APIRouter(prefix="/reserves", tags=["reserves"])


def get_reserves_service(session: AsyncSession = Depends(get_session)) -> ReservesService:
    return ReservesService(session)


@router.get("/proof", response_model=ProofOfReservesResponse)
async def get_proof_of_reserves(
    service: ReservesService = Depends(get_reserves_service),
):
    """
    Get Proof of Reserves.
    
    Returns the total physical gold holdings compared to
    the on-chain token supply, with coverage ratio.
    """
    proof = await service.get_proof_of_reserves()
    return ProofOfReservesResponse(**proof)


@router.get("/lookup", response_model=GoldBarResponse)
async def lookup_gold_bar(
    serial: str = Query(..., description="Gold bar serial number"),
    service: ReservesService = Depends(get_reserves_service),
):
    """
    Lookup a specific gold bar by serial number.
    
    Allows verification that a specific gold bar is in reserves.
    """
    bar = await service.lookup_gold_bar(serial)
    if not bar:
        raise HTTPException(
            status_code=404,
            detail=f"Gold bar with serial {serial} not found",
        )

    return GoldBarResponse(
        id=str(bar.id),
        serial_number=bar.serial_number,
        weight_grams=bar.weight_grams,
        purity=bar.purity,
        vault_location=bar.vault_location,
        acquired_at=bar.acquired_at,
        status=bar.status,
        created_at=bar.created_at,
    )


@router.get("/bars", response_model=GoldBarListResponse)
async def list_gold_bars(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str = Query(default=None, description="Filter by status"),
    service: ReservesService = Depends(get_reserves_service),
):
    """
    List all gold bars in reserves.
    
    Returns paginated list of gold bars backing the tokens.
    """
    bars = await service.get_all_gold_bars(
        limit=limit,
        offset=offset,
        status=status,
    )

    bar_responses = [
        GoldBarResponse(
            id=str(bar.id),
            serial_number=bar.serial_number,
            weight_grams=bar.weight_grams,
            purity=bar.purity,
            vault_location=bar.vault_location,
            acquired_at=bar.acquired_at,
            status=bar.status,
            created_at=bar.created_at,
        )
        for bar in bars
    ]

    return GoldBarListResponse(
        bars=bar_responses,
        total=len(bar_responses),
        limit=limit,
        offset=offset,
    )
