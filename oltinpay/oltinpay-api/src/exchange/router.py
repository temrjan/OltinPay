"""Exchange router."""

from uuid import UUID

from fastapi import APIRouter, Query

from src.auth.dependencies import CurrentUser, DbSession
from src.exchange import service
from src.exchange.schemas import (
    OrderBookResponse,
    OrderRequest,
    OrderResponse,
    PriceResponse,
    TradeResponse,
)

router = APIRouter()


@router.get("/orderbook", response_model=OrderBookResponse)
async def get_orderbook(db: DbSession) -> OrderBookResponse:
    """Get current orderbook."""
    return await service.get_orderbook(db)


@router.get("/price", response_model=PriceResponse)
async def get_price(db: DbSession) -> PriceResponse:
    """Get current bid/ask/mid price."""
    return await service.get_price(db)


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: OrderRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> OrderResponse:
    """Create a new order.

    Buy: spend USD, receive OLTIN
    Sell: spend OLTIN, receive USD
    Fee: 0.1% per trade
    """
    order = await service.create_order(
        db,
        user_id=current_user.id,
        side=request.side,
        order_type=request.type,
        price=request.price,
        quantity=request.quantity,
    )

    return OrderResponse.model_validate(order)


@router.get("/orders", response_model=list[OrderResponse])
async def get_orders(
    current_user: CurrentUser,
    db: DbSession,
    status: str | None = Query(None, pattern="^(open|partial|filled|cancelled)$"),
) -> list[OrderResponse]:
    """Get user's orders."""
    orders = await service.get_user_orders(
        db,
        user_id=current_user.id,
        status=status,
    )
    return [OrderResponse.model_validate(o) for o in orders]


@router.delete("/orders/{order_id}", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> OrderResponse:
    """Cancel an open order."""
    order = await service.cancel_order(
        db,
        order_id=order_id,
        user_id=current_user.id,
    )
    return OrderResponse.model_validate(order)


@router.get("/trades", response_model=list[TradeResponse])
async def get_trades(
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
) -> list[TradeResponse]:
    """Get recent trades."""
    trades = await service.get_recent_trades(db, limit=limit)
    return [
        TradeResponse(
            price=t.price,
            quantity=t.quantity,
            side="buy",  # Simplified
            created_at=t.created_at,
        )
        for t in trades
    ]
