"""Redis Pub/Sub for real-time updates."""

import asyncio
import json
from typing import Callable, Any

import redis.asyncio as redis
import structlog

from app.config import settings

logger = structlog.get_logger()


class PubSubManager:
    """Redis Pub/Sub manager for broadcasting messages."""

    def __init__(self):
        self.redis: redis.Redis | None = None
        self.pubsub: redis.client.PubSub | None = None
        self._listeners: dict[str, list[Callable]] = {}
        self._running = False

    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = redis.from_url(settings.redis_url)
            self.pubsub = self.redis.pubsub()
            logger.info("redis_pubsub_connected")
        except Exception as e:
            logger.error("redis_pubsub_connect_failed", error=str(e))
            raise

    async def disconnect(self):
        """Disconnect from Redis."""
        self._running = False
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        logger.info("redis_pubsub_disconnected")

    async def publish(self, channel: str, message: dict[str, Any]):
        """Publish message to channel."""
        if not self.redis:
            logger.warning("redis_not_connected")
            return

        try:
            data = json.dumps(message)
            await self.redis.publish(channel, data)
            logger.debug("pubsub_published", channel=channel)
        except Exception as e:
            logger.error("pubsub_publish_failed", channel=channel, error=str(e))

    async def subscribe(self, channel: str, callback: Callable):
        """Subscribe to channel with callback."""
        if channel not in self._listeners:
            self._listeners[channel] = []
            if self.pubsub:
                await self.pubsub.subscribe(channel)

        self._listeners[channel].append(callback)
        logger.info("pubsub_subscribed", channel=channel)

    async def start_listening(self):
        """Start listening for messages."""
        if not self.pubsub:
            return

        self._running = True
        logger.info("pubsub_listener_started")

        while self._running:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message:
                    channel = message["channel"].decode()
                    data = json.loads(message["data"].decode())

                    if channel in self._listeners:
                        for callback in self._listeners[channel]:
                            try:
                                await callback(data)
                            except Exception as e:
                                logger.error(
                                    "pubsub_callback_error",
                                    channel=channel,
                                    error=str(e),
                                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("pubsub_listen_error", error=str(e))
                await asyncio.sleep(1)


# Channels
CHANNEL_PRICE = "oltinchain:price"
CHANNEL_TRANSACTIONS = "oltinchain:transactions"
CHANNEL_METRICS = "oltinchain:metrics"


# Global instance
pubsub = PubSubManager()
