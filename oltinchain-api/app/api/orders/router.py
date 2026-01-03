"""Orders API router."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.orders.schemas import (
    BuyOrderRequest,
    OrderListResponse,
    OrderResponse,
    SellOrderRequest,
)
from app.application.services.order_service import OrderService
from app.application.services.price_service import PriceService
from app.database import get_session
from app.domain.exceptions import BlockchainError, InsufficientBalanceError
from app.infrastructure.blockchain import ZkSyncClient
from app.infrastructure.repositories.balance_repo import BalanceRepository
from app.infrastructure.repositories.order_repo import OrderRepository

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    """Get order service dependency."""
    order_repo = OrderRepository(session)
    balance_repo = BalanceRepository(session)
    blockchain = ZkSyncClient()
    price_service = PriceService()
    return OrderService(order_repo, balance_repo, blockchain, price_service)


@router.post("/buy", response_model=OrderResponse)
async def buy_order(
    data: BuyOrderRequest,
    user: CurrentUser,
    order_service: OrderService = Depends(get_order_service),
):
    """Buy OLTIN with USD.

    Creates an order, mints tokens on blockchain, updates balances.
    Price is determined by the Price Oracle based on current market cycle.
    User must have sufficient USD balance and a wallet address.
    """
    if not user.wallet_address:
        raise HTTPException(
            status_code=400,
            detail="Wallet address required. Update profile first.",
        )

    try:
        order = await order_service.buy(
            user_id=cast(UUID, user.id),
            wallet_address=user.wallet_address,
            amount_usd=data.amount_usd,
        )
        return OrderResponse.model_validate(order)
    except InsufficientBalanceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BlockchainError as e:
        raise HTTPException(status_code=500, detail=f"Blockchain error: {e}")


@router.post("/sell", response_model=OrderResponse)
async def sell_order(
    data: SellOrderRequest,
    user: CurrentUser,
    order_service: OrderService = Depends(get_order_service),
):
    """Sell OLTIN for USD.

    Creates an order, burns tokens on blockchain, updates balances.
    Price is determined by the Price Oracle based on current market cycle.
    User must have sufficient OLTIN balance and a wallet address.
    """
    if not user.wallet_address:
        raise HTTPException(
            status_code=400,
            detail="Wallet address required. Update profile first.",
        )

    try:
        order = await order_service.sell(
            user_id=cast(UUID, user.id),
            wallet_address=user.wallet_address,
            amount_oltin=data.amount_oltin,
        )
        return OrderResponse.model_validate(order)
    except InsufficientBalanceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BlockchainError as e:
        raise HTTPException(status_code=500, detail=f"Blockchain error: {e}")


@router.get("", response_model=OrderListResponse)
async def list_orders(
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    order_service: OrderService = Depends(get_order_service),
):
    """Get user's order history."""
    orders = await order_service.get_user_orders(cast(UUID, user.id), limit, offset)
    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=len(orders),
    )
