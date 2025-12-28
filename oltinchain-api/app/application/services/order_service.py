"""Order service for buy/sell operations."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import structlog

from app.application.interfaces.balance_repository import BalanceRepositoryProtocol
from app.application.interfaces.blockchain import BlockchainServiceProtocol
from app.application.interfaces.order_repository import OrderRepositoryProtocol
from app.application.services.price_service import PriceService
from app.application.services.broadcast_service import broadcast
from app.domain.exceptions import InsufficientBalanceError, OrderError, BlockchainError
from app.infrastructure.models import Order

logger = structlog.get_logger()


class OrderService:
    """Service for order operations (buy/sell gold)."""

    def __init__(
        self,
        order_repo: OrderRepositoryProtocol,
        balance_repo: BalanceRepositoryProtocol,
        blockchain: BlockchainServiceProtocol,
        price_service: PriceService | None = None,
    ):
        self.order_repo = order_repo
        self.balance_repo = balance_repo
        self.blockchain = blockchain
        self.price_service = price_service or PriceService()

    async def buy(self, user_id: UUID, wallet_address: str, amount_uzs: Decimal) -> Order:
        """Buy OLTIN with UZS."""
        # 1. Calculate quote
        quote = self.price_service.get_buy_quote(amount_uzs)

        logger.info(
            "buy_order_started",
            user_id=str(user_id),
            amount_uzs=str(amount_uzs),
            fee_uzs=str(quote.fee_uzs),
            oltin_amount=str(quote.amount_oltin),
        )

        # 2. Check and lock UZS balance
        try:
            await self.balance_repo.lock_funds(user_id, "UZS", amount_uzs)
        except InsufficientBalanceError:
            logger.warning("buy_order_insufficient_balance", user_id=str(user_id))
            raise

        # 3. Create order
        order = Order(
            user_id=user_id,
            type="buy",
            status="pending",
            amount_uzs=amount_uzs,
            amount_oltin=quote.amount_oltin,
            price_per_gram=quote.gold_price_per_gram,
            fee_uzs=quote.fee_uzs,
        )
        order = await self.order_repo.create(order)

        # 4. Mint tokens on blockchain
        try:
            tx_hash = await self.blockchain.mint(
                to_address=wallet_address,
                grams=quote.amount_oltin,
                order_id=str(order.id),
            )
            order.tx_hash = tx_hash
            order.status = "completed"
            order.completed_at = datetime.utcnow()

            # 5. Release locked UZS (it's spent)
            await self.balance_repo.release_locked(user_id, "UZS", amount_uzs)

            # 6. Add OLTIN to user balance
            await self.balance_repo.add_available(user_id, "OLTIN", quote.amount_oltin)

            logger.info(
                "buy_order_completed",
                order_id=str(order.id),
                tx_hash=tx_hash,
            )

            # 7. Broadcast to dashboard
            try:
                await broadcast.broadcast_order_completed(
                    user_id=user_id,
                    order_id=order.id,
                    order_type="buy",
                    amount_uzs=amount_uzs,
                    amount_oltin=quote.amount_oltin,
                    fee_uzs=quote.fee_uzs,
                    tx_hash=tx_hash,
                    wallet_address=wallet_address,
                )
            except Exception as e:
                logger.error("broadcast_failed", error=str(e))

        except BlockchainError as e:
            order.status = "failed"
            order.error_message = str(e)

            # Unlock UZS (return to user)
            await self.balance_repo.unlock_funds(user_id, "UZS", amount_uzs)

            logger.error(
                "buy_order_failed",
                order_id=str(order.id),
                error=str(e),
            )

        await self.order_repo.update(order)
        return order

    async def sell(self, user_id: UUID, wallet_address: str, amount_oltin: Decimal) -> Order:
        """Sell OLTIN for UZS."""
        # 1. Calculate quote
        quote = self.price_service.get_sell_quote(amount_oltin)

        logger.info(
            "sell_order_started",
            user_id=str(user_id),
            amount_oltin=str(amount_oltin),
            fee_uzs=str(quote.fee_uzs),
            net_uzs=str(quote.net_amount_uzs),
        )

        # 2. Check and lock OLTIN balance
        try:
            await self.balance_repo.lock_funds(user_id, "OLTIN", amount_oltin)
        except InsufficientBalanceError:
            logger.warning("sell_order_insufficient_balance", user_id=str(user_id))
            raise

        # 3. Create order
        order = Order(
            user_id=user_id,
            type="sell",
            status="pending",
            amount_uzs=quote.amount_uzs,
            amount_oltin=amount_oltin,
            price_per_gram=quote.gold_price_per_gram,
            fee_uzs=quote.fee_uzs,
        )
        order = await self.order_repo.create(order)

        # 4. Burn tokens on blockchain
        try:
            tx_hash = await self.blockchain.burn(
                from_address=wallet_address,
                grams=amount_oltin,
                order_id=str(order.id),
            )
            order.tx_hash = tx_hash
            order.status = "completed"
            order.completed_at = datetime.utcnow()

            # 5. Release locked OLTIN (it's burned)
            await self.balance_repo.release_locked(user_id, "OLTIN", amount_oltin)

            # 6. Add UZS to user balance (net after fee)
            await self.balance_repo.add_available(user_id, "UZS", quote.net_amount_uzs)

            logger.info(
                "sell_order_completed",
                order_id=str(order.id),
                tx_hash=tx_hash,
            )

            # 7. Broadcast to dashboard
            try:
                await broadcast.broadcast_order_completed(
                    user_id=user_id,
                    order_id=order.id,
                    order_type="sell",
                    amount_uzs=quote.amount_uzs,
                    amount_oltin=amount_oltin,
                    fee_uzs=quote.fee_uzs,
                    tx_hash=tx_hash,
                    wallet_address=wallet_address,
                )
            except Exception as e:
                logger.error("broadcast_failed", error=str(e))

        except BlockchainError as e:
            order.status = "failed"
            order.error_message = str(e)

            # Unlock OLTIN (return to user)
            await self.balance_repo.unlock_funds(user_id, "OLTIN", amount_oltin)

            logger.error(
                "sell_order_failed",
                order_id=str(order.id),
                error=str(e),
            )

        await self.order_repo.update(order)
        return order

    async def get_user_orders(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Order]:
        """Get user's order history."""
        return await self.order_repo.get_user_orders(user_id, limit, offset)

    async def get_order(self, order_id: UUID) -> Order | None:
        """Get order by ID."""
        return await self.order_repo.get_by_id(order_id)
