"""Public PoR / rates / quote service — reads live chain state.

Math is taken directly from the on-chain contracts so the dashboard matches
what users actually get:

  * OltinTokenV3: ``1 OLTIN == 1 gram``; mint cap = ``reserveAnswer *
    10**(18 - reserveDecimals)``. PoR coverage = attested grams / OLTIN in
    circulation (>= 1.0 == fully backed).
  * Exchange: ``GRAMS_PER_OZ_1E8 = 3110347680``; buy/sell use the XAU/USD and
    UZS/USD feeds (both 8 decimals), floored, exactly like Exchange.buy/sell.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import select

from src.common.exceptions import BadRequestException
from src.config import settings
from src.indexer.models import ChainEvent, ChainEventType
from src.infrastructure import chain_read
from src.por.schemas import (
    FeedReading,
    PorContractAddresses,
    PorHistoryItem,
    PorResponse,
    QuoteResponse,
    QuoteSide,
    RatesResponse,
)

if TYPE_CHECKING:
    from decimal import Decimal

    from sqlalchemy.ext.asyncio import AsyncSession

OLTIN_DECIMALS = 18
# Grams per troy ounce * 1e8 (mirrors Exchange.GRAMS_PER_OZ_1E8).
GRAMS_PER_OZ_1E8 = 3110347680


def _pow10(exp: int) -> int:
    """``10**exp`` as a concrete int (int.__pow__ is typed Any for non-literals)."""
    return int(10**exp)


async def get_por() -> PorResponse:
    """Live proof-of-reserve snapshot."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        reserve, reserve_decimals, supply_wei = await asyncio.gather(
            chain_read.latest_round_data(
                settings.reserve_attestor_address, client=client
            ),
            chain_read.feed_decimals(settings.reserve_attestor_address, client=client),
            chain_read.total_supply(settings.oltin_contract_address, client=client),
        )

    reserve_grams = (
        reserve.answer / _pow10(reserve_decimals) if reserve_decimals >= 0 else 0.0
    )
    oltin_supply = supply_wei / _pow10(OLTIN_DECIMALS)
    coverage = reserve_grams / oltin_supply if oltin_supply > 0 else None

    return PorResponse(
        reserve_answer=str(reserve.answer),
        reserve_decimals=reserve_decimals,
        reserve_grams=reserve_grams,
        reserve_updated_at=reserve.updated_at,
        oltin_total_supply_wei=str(supply_wei),
        oltin_decimals=OLTIN_DECIMALS,
        oltin_supply=oltin_supply,
        coverage_ratio=coverage,
        contracts=PorContractAddresses(
            oltin=settings.oltin_contract_address,
            uzd=settings.uzd_contract_address,
            reserve_attestor=settings.reserve_attestor_address,
            exchange=settings.exchange_address,
        ),
    )


async def get_por_history(db: AsyncSession, limit: int = 50) -> list[PorHistoryItem]:
    """Reserve attestations recorded by the indexer, newest first."""
    result = await db.execute(
        select(ChainEvent)
        .where(ChainEvent.event_type == ChainEventType.RESERVE_ANSWER.value)
        .order_by(ChainEvent.block_number.desc())
        .limit(limit)
    )
    return [
        PorHistoryItem(
            answer=event.answer or "0",
            block_number=event.block_number,
            tx_hash=event.tx_hash,
            indexed_at=event.created_at,
        )
        for event in result.scalars().all()
    ]


async def _read_feeds(
    client: httpx.AsyncClient,
) -> tuple[chain_read.RoundData, int, chain_read.RoundData, int]:
    xau, xau_dec, uzs, uzs_dec = await asyncio.gather(
        chain_read.latest_round_data(settings.xau_feed_address, client=client),
        chain_read.feed_decimals(settings.xau_feed_address, client=client),
        chain_read.latest_round_data(settings.uzs_feed_address, client=client),
        chain_read.feed_decimals(settings.uzs_feed_address, client=client),
    )
    return xau, xau_dec, uzs, uzs_dec


def _oltin_price_uzd(xau_answer: int, uzs_answer: int) -> float:
    """UZS per 1 OLTIN (== sell of 1 OLTIN), using the Exchange formula."""
    unit_wei = (_pow10(OLTIN_DECIMALS) * xau_answer * _pow10(8)) // (
        GRAMS_PER_OZ_1E8 * uzs_answer
    )
    return unit_wei / _pow10(OLTIN_DECIMALS)


async def get_rates() -> RatesResponse:
    """Live XAU/USD and UZS/USD readings plus the derived OLTIN price."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        xau, xau_dec, uzs, uzs_dec = await _read_feeds(client)

    if xau.answer <= 0 or uzs.answer <= 0:
        raise BadRequestException("Price feeds unavailable")

    return RatesResponse(
        xau_usd=FeedReading(
            answer=str(xau.answer), decimals=xau_dec, updated_at=xau.updated_at
        ),
        uzs_usd=FeedReading(
            answer=str(uzs.answer), decimals=uzs_dec, updated_at=uzs.updated_at
        ),
        oltin_price_uzd=_oltin_price_uzd(xau.answer, uzs.answer),
    )


async def get_quote(side: QuoteSide | None, amount: Decimal | None) -> QuoteResponse:
    """Buy/sell price preview. If ``side`` and ``amount`` are given, estimate out."""
    if amount is not None and side is None:
        raise BadRequestException("side is required when amount is provided")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Two independent feed reads — gather (P2), matching get_por/get_rates.
        xau, uzs = await asyncio.gather(
            chain_read.latest_round_data(settings.xau_feed_address, client=client),
            chain_read.latest_round_data(settings.uzs_feed_address, client=client),
        )

    if xau.answer <= 0 or uzs.answer <= 0:
        raise BadRequestException("Price feeds unavailable")

    response = QuoteResponse(
        oltin_price_uzd=_oltin_price_uzd(xau.answer, uzs.answer),
        xau_answer=str(xau.answer),
        uzs_answer=str(uzs.answer),
        xau_updated_at=xau.updated_at,
        uzs_updated_at=uzs.updated_at,
        side=side,
        amount=float(amount) if amount is not None else None,
    )

    if amount is not None and side is not None:
        if amount <= 0:
            raise BadRequestException("amount must be positive")
        if side is QuoteSide.BUY:
            # Spend UZD -> receive OLTIN (Exchange.buy formula, floored).
            uzd_in_wei = int(amount * _pow10(OLTIN_DECIMALS))
            out_wei = (uzd_in_wei * uzs.answer * GRAMS_PER_OZ_1E8) // (
                _pow10(8) * xau.answer
            )
            response.estimated_out_symbol = "OLTIN"
        else:
            # Spend OLTIN -> receive UZD (Exchange.sell formula, floored).
            oltin_in_wei = int(amount * _pow10(OLTIN_DECIMALS))
            out_wei = (oltin_in_wei * xau.answer * _pow10(8)) // (
                GRAMS_PER_OZ_1E8 * uzs.answer
            )
            response.estimated_out_symbol = "UZD"
        response.estimated_out_wei = str(out_wei)
        response.estimated_out = out_wei / _pow10(OLTIN_DECIMALS)

    return response
