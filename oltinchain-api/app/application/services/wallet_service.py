"""Wallet service for balance and transaction management."""

from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import Balance, Transaction, Order
from app.infrastructure.blockchain.zksync_client import ZkSyncClient
from app.domain.exceptions import BlockchainError

logger = structlog.get_logger()


class WalletService:
    """Service for wallet operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_balances(self, user_id: UUID) -> dict[str, dict]:
        """Get all balances for a user."""
        result = await self.session.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
        balances = result.scalars().all()

        balance_map = {
            "USD": {"available": Decimal("0"), "locked": Decimal("0")},
            "OLTIN": {"available": Decimal("0"), "locked": Decimal("0")},
        }

        for b in balances:
            if b.asset in balance_map:
                balance_map[b.asset] = {
                    "available": b.available,
                    "locked": b.locked,
                }

        return balance_map

    async def update_balance(
        self,
        user_id: UUID,
        asset: str,
        delta: Decimal,
    ) -> Decimal:
        """Update user balance by delta amount.
        
        Args:
            user_id: User UUID
            asset: Asset code (UZS, OLTIN)
            delta: Amount to add (positive) or subtract (negative)
            
        Returns:
            New available balance
        """
        result = await self.session.execute(
            select(Balance).where(
                Balance.user_id == user_id,
                Balance.asset == asset,
            )
        )
        balance = result.scalar_one_or_none()
        
        if balance:
            balance.available += delta
            balance.updated_at = datetime.utcnow()
        else:
            balance = Balance(
                id=uuid4(),
                user_id=user_id,
                asset=asset,
                available=delta,
                locked=Decimal("0"),
                updated_at=datetime.utcnow(),
            )
            self.session.add(balance)
        
        await self.session.commit()
        await self.session.refresh(balance)
        
        logger.info(
            "balance_updated",
            user_id=str(user_id),
            asset=asset,
            delta=str(delta),
            new_balance=str(balance.available),
        )
        
        return balance.available

    async def record_transfer(
        self,
        user_id: UUID,
        to_address: str,
        amount: Decimal,
        tx_hash: str,
    ) -> Transaction:
        """Record a transfer transaction."""
        tx = Transaction(
            id=uuid4(),
            user_id=user_id,
            type="transfer",
            asset="OLTIN",
            amount=-amount,  # Negative for outgoing
            to_address=to_address,
            tx_hash=tx_hash,
            status="completed",
            created_at=datetime.utcnow(),
        )
        self.session.add(tx)
        await self.session.commit()
        
        logger.info(
            "transfer_recorded",
            user_id=str(user_id),
            to_address=to_address,
            amount=str(amount),
            tx_hash=tx_hash,
        )
        
        return tx

    async def get_transactions(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        """Get transaction history for a user."""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(desc(Transaction.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_transactions_from_orders(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        """Get completed orders as transactions."""
        result = await self.session.execute(
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.status == "completed",
            )
            .order_by(desc(Order.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def sync_blockchain_balance(
        self,
        user_id: UUID,
        wallet_address: str,
    ) -> dict:
        """Sync local OLTIN balance with blockchain."""
        try:
            client = ZkSyncClient()
            on_chain_balance = await client.get_balance(wallet_address)

            result = await self.session.execute(
                select(Balance).where(
                    Balance.user_id == user_id,
                    Balance.asset == "OLTIN",
                )
            )
            local_balance = result.scalar_one_or_none()
            local_available = local_balance.available if local_balance else Decimal("0")
            local_locked = local_balance.locked if local_balance else Decimal("0")
            local_total = local_available + local_locked

            discrepancy = on_chain_balance - local_total
            is_synced = abs(discrepancy) < Decimal("0.0001")

            if not is_synced:
                logger.warning(
                    "balance_discrepancy",
                    user_id=str(user_id),
                    wallet=wallet_address,
                    on_chain=str(on_chain_balance),
                    local=str(local_total),
                    discrepancy=str(discrepancy),
                )

            return {
                "wallet_address": wallet_address,
                "on_chain_balance": on_chain_balance,
                "local_available": local_available,
                "local_locked": local_locked,
                "local_total": local_total,
                "is_synced": is_synced,
                "discrepancy": discrepancy if not is_synced else None,
            }

        except BlockchainError as e:
            logger.error("sync_balance_failed", error=str(e))
            return {
                "wallet_address": wallet_address,
                "error": str(e),
                "is_synced": False,
            }

    async def deposit_uzs(self, user_id: UUID, amount: Decimal) -> dict:
        """Deposit UZS to user wallet (for testing/demo)."""
        new_balance = await self.update_balance(user_id, "USD", amount)
        
        return {
            "success": True,
            "new_balance": new_balance,
            "message": f"Deposited {amount} UZS",
        }

    async def get_all_history(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get combined history: orders + transfers."""
        from sqlalchemy import union_all, literal, case
        from app.infrastructure.models import Transaction

        # Orders
        orders_q = (
            select(
                Order.id.label("id"),
                Order.type.label("type"),
                case(
                    (Order.type == "buy", literal("OLTIN")),
                    else_=literal("USD")
                ).label("asset"),
                case(
                    (Order.type == "buy", Order.amount_oltin),
                    else_=Order.amount_uzs
                ).label("amount"),
                Order.amount_uzs.label("amount_uzs"),
                Order.amount_oltin.label("amount_oltin"),
                Order.fee_uzs.label("fee_uzs"),
                Order.tx_hash.label("tx_hash"),
                literal(None).label("to_address"),
                Order.status.label("status"),
                Order.created_at.label("created_at"),
            )
            .where(
                Order.user_id == user_id,
                Order.status == "completed",
            )
        )

        # Transfers
        transfers_q = (
            select(
                Transaction.id.label("id"),
                Transaction.type.label("type"),
                Transaction.asset.label("asset"),
                Transaction.amount.label("amount"),
                literal(None).label("amount_uzs"),
                literal(None).label("amount_oltin"),
                literal(None).label("fee_uzs"),
                Transaction.tx_hash.label("tx_hash"),
                Transaction.to_address.label("to_address"),
                Transaction.status.label("status"),
                Transaction.created_at.label("created_at"),
            )
            .where(Transaction.user_id == user_id)
        )

        combined = union_all(orders_q, transfers_q).subquery()
        
        result = await self.session.execute(
            select(combined)
            .order_by(desc(combined.c.created_at))
            .limit(limit)
            .offset(offset)
        )

        return [dict(row._mapping) for row in result.fetchall()]
