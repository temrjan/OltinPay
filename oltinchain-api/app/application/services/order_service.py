"""Order service for buy/sell operations."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import structlog

from app.application.interfaces.balance_repository import BalanceRepositoryProtocol
from app.application.interfaces.blockchain import BlockchainServiceProtocol
from app.application.interfaces.order_repository import OrderRepositoryProtocol
from app.application.services.broadcast_service import broadcast
from app.application.services.price_service import PriceService
from app.domain.exceptions import BlockchainError, InsufficientBalanceError
from app.infrastructure.models import Order

logger = structlog.get_logger()


class OrderService:
    """Service for order operations (buy/sell OLTIN).

    Uses Price Oracle for dynamic pricing based on market cycles.
    """

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

    async def buy(
        self,
        user_id: UUID,
        wallet_address: str,
        amount_usd: Decimal,
    ) -> Order:
        """Buy OLTIN with USD.

        Args:
            user_id: User UUID.
            wallet_address: User's blockchain wallet.
            amount_usd: Amount to spend in USD.

        Returns:
            Created order.
        """
        # 1. Get quote from Price Oracle
        quote = self.price_service.get_buy_quote(amount_usd)

        logger.info(
            "buy_order_started",
            user_id=str(user_id),
            amount_usd=str(amount_usd),
            fee_usd=str(quote.fee_usd),
            oltin_amount=str(quote.amount_oltin),
            price=str(quote.price_per_gram),
        )

        # 2. Check and lock USD balance
        try:
            await self.balance_repo.lock_funds(user_id, "USD", amount_usd)
        except InsufficientBalanceError:
            logger.warning("buy_order_insufficient_balance", user_id=str(user_id))
            raise

        # 3. Create order (DB fields still named _uzs for compatibility)
        order = Order(
            user_id=user_id,
            type="buy",
            status="pending",
            amount_uzs=amount_usd,  # USD stored in uzs field
            amount_oltin=quote.amount_oltin,
            price_per_gram=quote.price_per_gram,
            fee_uzs=quote.fee_usd,  # USD fee stored in uzs field
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
            order.completed_at = datetime.now(timezone.utc)

            # 5. Release locked USD (spent)
            await self.balance_repo.release_locked(user_id, "USD", amount_usd)

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
                    amount_uzs=amount_usd,
                    amount_oltin=quote.amount_oltin,
                    fee_uzs=quote.fee_usd,
                    tx_hash=tx_hash,
                    wallet_address=wallet_address,
                )
            except Exception as e:
                logger.error("broadcast_failed", error=str(e))

        except BlockchainError as e:
            order.status = "failed"
            order.error_message = str(e)

            # Unlock USD (return to user)
            await self.balance_repo.unlock_funds(user_id, "USD", amount_usd)

            logger.error(
                "buy_order_failed",
                order_id=str(order.id),
                error=str(e),
            )

        await self.order_repo.update(order)
        return order

    async def sell(
        self,
        user_id: UUID,
        wallet_address: str,
        amount_oltin: Decimal,
    ) -> Order:
        """Sell OLTIN for USD.

        Args:
            user_id: User UUID.
            wallet_address: User's blockchain wallet.
            amount_oltin: Amount of OLTIN to sell.

        Returns:
            Created order.
        """
        # 1. Get quote from Price Oracle
        quote = self.price_service.get_sell_quote(amount_oltin)

        logger.info(
            "sell_order_started",
            user_id=str(user_id),
            amount_oltin=str(amount_oltin),
            fee_usd=str(quote.fee_usd),
            net_usd=str(quote.net_amount_usd),
            price=str(quote.price_per_gram),
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
            amount_uzs=quote.amount_usd,
            amount_oltin=amount_oltin,
            price_per_gram=quote.price_per_gram,
            fee_uzs=quote.fee_usd,
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
            order.completed_at = datetime.now(timezone.utc)

            # 5. Release locked OLTIN (burned)
            await self.balance_repo.release_locked(user_id, "OLTIN", amount_oltin)

            # 6. Add USD to user balance (net after fee)
            await self.balance_repo.add_available(user_id, "USD", quote.net_amount_usd)

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
                    amount_uzs=quote.amount_usd,
                    amount_oltin=amount_oltin,
                    fee_uzs=quote.fee_usd,
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
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        """Get user's order history."""
        return await self.order_repo.get_user_orders(user_id, limit, offset)

    async def get_order(self, order_id: UUID) -> Order | None:
        """Get order by ID."""
        return await self.order_repo.get_by_id(order_id)
