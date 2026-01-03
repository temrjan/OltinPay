"""OrderBook API router."""

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_session
from app.api.orderbook.schemas import (
    LimitOrderResponse,
    OrderBookResponse,
    PlaceOrderRequest,
    PlaceOrderResponse,
    RecentTradesResponse,
    TradeResponse,
    UserOrdersResponse,
)
from app.application.services.orderbook_service import OrderBookService

router = APIRouter(prefix="/orderbook", tags=["orderbook"])


def get_orderbook_service(
    session: AsyncSession = Depends(get_session),
) -> OrderBookService:
    """Get orderbook service dependency."""
    return OrderBookService(session)


@router.get("", response_model=OrderBookResponse)
async def get_orderbook(
    depth: int = Query(default=20, ge=1, le=100),
    service: OrderBookService = Depends(get_orderbook_service),
):
    """Get current order book.

    Returns aggregated bid and ask levels.
    """
    return await service.get_orderbook(depth)


@router.post("/orders", response_model=PlaceOrderResponse)
async def place_order(
    data: PlaceOrderRequest,
    user: CurrentUser,
    service: OrderBookService = Depends(get_orderbook_service),
):
    """Place a new limit order.

    Order will be matched against existing orders if possible.
    Remaining quantity stays in the order book.
    """
    try:
        order, trades = await service.place_order(
            user_id=cast(UUID, user.id),
            side=data.side,
            price=data.price,
            quantity=data.quantity,
        )

        trades_count = len(trades)
        if trades_count > 0:
            message = f"Order placed and {trades_count} trade(s) executed"
        else:
            message = "Order placed in order book"

        return PlaceOrderResponse(
            order=LimitOrderResponse(
                id=cast(UUID, order.id),
                user_id=cast(UUID, order.user_id),
                side=order.side,
                price=order.price,
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                remaining_quantity=order.remaining_quantity,
                status=order.status,
                created_at=order.created_at,
                updated_at=order.updated_at,
                filled_at=order.filled_at,
            ),
            trades=[TradeResponse.model_validate(t) for t in trades],
            message=message,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/orders/{order_id}", response_model=LimitOrderResponse)
async def cancel_order(
    order_id: UUID,
    user: CurrentUser,
    service: OrderBookService = Depends(get_orderbook_service),
):
    """Cancel an open limit order."""
    try:
        order = await service.cancel_order(order_id, cast(UUID, user.id))
        return LimitOrderResponse(
            id=cast(UUID, order.id),
            user_id=cast(UUID, order.user_id),
            side=order.side,
            price=order.price,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            remaining_quantity=order.remaining_quantity,
            status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at,
            filled_at=order.filled_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders", response_model=UserOrdersResponse)
async def get_my_orders(
    user: CurrentUser,
    status: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100),
    service: OrderBookService = Depends(get_orderbook_service),
):
    """Get current user's limit orders."""
    orders = await service.get_user_orders(cast(UUID, user.id), status, limit)
    return UserOrdersResponse(
        orders=[
            LimitOrderResponse(
                id=cast(UUID, o.id),
                user_id=cast(UUID, o.user_id),
                side=o.side,
                price=o.price,
                quantity=o.quantity,
                filled_quantity=o.filled_quantity,
                remaining_quantity=o.remaining_quantity,
                status=o.status,
                created_at=o.created_at,
                updated_at=o.updated_at,
                filled_at=o.filled_at,
            )
            for o in orders
        ],
        total=len(orders),
    )


@router.get("/trades", response_model=RecentTradesResponse)
async def get_recent_trades(
    limit: int = Query(default=50, ge=1, le=100),
    service: OrderBookService = Depends(get_orderbook_service),
):
    """Get recent trades."""
    trades = await service.get_recent_trades(limit)
    return RecentTradesResponse(
        trades=[TradeResponse.model_validate(t) for t in trades],
    )
