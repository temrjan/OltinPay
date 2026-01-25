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
    SwapQuoteResponse,
    SwapRequest,
    SwapResponse,
    TradeResponse,
)

router = APIRouter()


@router.get("/orderbook", response_model=OrderBookResponse)
async def get_orderbook(db: DbSession) -> OrderBookResponse:
    """Get current orderbook."""
    return await service.get_orderbook(db)


@router.get("/price", response_model=PriceResponse)
async def get_price(db: DbSession) -> PriceResponse:
    """Get current bid/ask/mid price (real gold price)."""
    return await service.get_price(db)


# ===== SWAP ENDPOINTS (recommended) =====


@router.post("/swap/quote", response_model=SwapQuoteResponse)
async def get_swap_quote(
    request: SwapRequest,
    current_user: CurrentUser,
) -> SwapQuoteResponse:
    """Get swap quote without executing.

    - side: 'buy' = USD -> OLTIN, 'sell' = OLTIN -> USD
    - amount: Amount to swap
    - amount_type: 'from' = what you give, 'to' = what you want to receive
    """
    return await service.get_swap_quote(
        side=request.side,
        amount=request.amount,
        amount_type=request.amount_type,
    )


@router.post("/swap", response_model=SwapResponse)
async def execute_swap(
    request: SwapRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SwapResponse:
    """Execute instant swap on exchange account.

    Requires funds on exchange account.
    Use /send (internal transfer) to move funds from wallet to exchange first.
    """
    return await service.execute_swap(
        db=db,
        user_id=current_user.id,
        side=request.side,
        amount=request.amount,
        amount_type=request.amount_type,
    )


# ===== LEGACY ORDER ENDPOINTS =====


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: OrderRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> OrderResponse:
    """Create a new order (legacy - prefer /swap for instant execution)."""
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
            side="buy",
            created_at=t.created_at,
        )
        for t in trades
    ]
