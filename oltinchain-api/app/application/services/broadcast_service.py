"""Broadcast service for real-time updates."""

from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID
from typing import Any

import structlog

from app.api.ws.manager import manager
from app.infrastructure.pubsub import pubsub, CHANNEL_PRICE, CHANNEL_TRANSACTIONS, CHANNEL_METRICS

logger = structlog.get_logger()


class BroadcastService:
    """Service for broadcasting real-time updates."""

    @staticmethod
    async def broadcast_price_update(
        price_uzs: Decimal,
        price_usd: Decimal | None = None,
    ):
        """Broadcast gold price update to all subscribers."""
        message = {
            "type": "price_update",
            "data": {
                "price_per_gram_uzs": str(price_uzs),
                "price_per_gram_usd": str(price_usd) if price_usd else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        # Send via WebSocket
        await manager.broadcast_to_channel("price", message)

        # Publish to Redis for other instances
        await pubsub.publish(CHANNEL_PRICE, message)

        logger.info("price_update_broadcast", price=str(price_uzs))

    @staticmethod
    async def broadcast_transaction(
        user_id: UUID,
        tx_type: str,
        amount_uzs: Decimal,
        amount_oltin: Decimal,
        tx_hash: str | None = None,
    ):
        """Broadcast transaction update to specific user."""
        message = {
            "type": "transaction",
            "data": {
                "tx_type": tx_type,
                "amount_uzs": str(amount_uzs),
                "amount_oltin": str(amount_oltin),
                "tx_hash": tx_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        # Send to specific user
        await manager.send_personal(user_id, message)

        logger.info(
            "transaction_broadcast",
            user_id=str(user_id),
            tx_type=tx_type,
        )

    @staticmethod
    async def broadcast_public_transaction(
        tx_type: str,
        address: str,
        amount_oltin: Decimal,
        tx_hash: str | None = None,
    ):
        """Broadcast transaction to public transactions channel."""
        message = {
            "type": "transaction",
            "data": {
                "tx_type": "mint" if tx_type == "buy" else "burn",
                "tx_hash": tx_hash or "",
                "address": address,
                "amount": str(amount_oltin),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        # Send to transactions channel (public dashboard)
        await manager.broadcast_to_channel("transactions", message)
        await pubsub.publish(CHANNEL_TRANSACTIONS, message)

        logger.info(
            "public_transaction_broadcast",
            tx_type=tx_type,
            amount=str(amount_oltin),
        )

    @staticmethod
    async def broadcast_metrics(metrics: dict[str, Any]):
        """Broadcast system metrics to all subscribers."""
        message = {
            "type": "metrics",
            "data": {
                **metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        await manager.broadcast_to_channel("metrics", message)
        await pubsub.publish(CHANNEL_METRICS, message)

    @staticmethod
    async def broadcast_order_completed(
        user_id: UUID,
        order_id: UUID,
        order_type: str,
        amount_uzs: Decimal,
        amount_oltin: Decimal,
        fee_uzs: Decimal,
        tx_hash: str | None = None,
        wallet_address: str | None = None,
    ):
        """Broadcast order completion to user and public channel."""
        message = {
            "type": "order_completed",
            "data": {
                "order_id": str(order_id),
                "order_type": order_type,
                "amount_uzs": str(amount_uzs),
                "amount_oltin": str(amount_oltin),
                "fee_uzs": str(fee_uzs),
                "tx_hash": tx_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        await manager.send_personal(user_id, message)

        # Also broadcast to public transactions channel
        if wallet_address and tx_hash:
            await BroadcastService.broadcast_public_transaction(
                tx_type=order_type,
                address=wallet_address,
                amount_oltin=amount_oltin,
                tx_hash=tx_hash,
            )

        logger.info(
            "order_completed_broadcast",
            user_id=str(user_id),
            order_id=str(order_id),
        )


# Global instance
broadcast = BroadcastService()
