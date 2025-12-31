"""WebSocket connection manager."""

import asyncio
import json
from typing import Any
from uuid import UUID

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: dict[str, set[WebSocket]] = {}
        # All connections for broadcast
        self.all_connections: set[WebSocket] = set()
        # Channels subscriptions: channel -> set of websockets
        self.channels: dict[str, set[WebSocket]] = {
            "price": set(),
            "transactions": set(),
            "metrics": set(),
            "orderbook": set(),
            "trades": set(),
        }

    async def connect(
        self,
        websocket: WebSocket,
        user_id: UUID | None = None,
        channels: list[str] | None = None,
    ):
        """Accept and register a new connection."""
        await websocket.accept()
        self.all_connections.add(websocket)

        if user_id:
            user_key = str(user_id)
            if user_key not in self.active_connections:
                self.active_connections[user_key] = set()
            self.active_connections[user_key].add(websocket)

        # Subscribe to channels
        if channels:
            for channel in channels:
                if channel in self.channels:
                    self.channels[channel].add(websocket)

        logger.info(
            "websocket_connected",
            user_id=str(user_id) if user_id else None,
            channels=channels,
            total_connections=len(self.all_connections),
        )

    async def disconnect(self, websocket: WebSocket, user_id: UUID | None = None):
        """Remove a connection."""
        self.all_connections.discard(websocket)

        if user_id:
            user_key = str(user_id)
            if user_key in self.active_connections:
                self.active_connections[user_key].discard(websocket)
                if not self.active_connections[user_key]:
                    del self.active_connections[user_key]

        # Remove from all channels
        for channel_sockets in self.channels.values():
            channel_sockets.discard(websocket)

        logger.info(
            "websocket_disconnected",
            user_id=str(user_id) if user_id else None,
            total_connections=len(self.all_connections),
        )

    async def send_personal(self, user_id: UUID, message: dict[str, Any]):
        """Send message to specific user."""
        user_key = str(user_id)
        if user_key in self.active_connections:
            data = json.dumps(message)
            for websocket in self.active_connections[user_key].copy():
                try:
                    await websocket.send_text(data)
                except Exception as e:
                    logger.error("websocket_send_failed", error=str(e))
                    await self.disconnect(websocket, user_id)

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast message to all connections."""
        data = json.dumps(message)
        for websocket in self.all_connections.copy():
            try:
                await websocket.send_text(data)
            except Exception as e:
                logger.error("websocket_broadcast_failed", error=str(e))
                self.all_connections.discard(websocket)

    async def broadcast_to_channel(self, channel: str, message: dict[str, Any]):
        """Broadcast message to all subscribers of a channel."""
        if channel not in self.channels:
            return

        data = json.dumps(message)
        for websocket in self.channels[channel].copy():
            try:
                await websocket.send_text(data)
            except Exception as e:
                logger.error("websocket_channel_failed", channel=channel, error=str(e))
                self.channels[channel].discard(websocket)

    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "total_connections": len(self.all_connections),
            "users_connected": len(self.active_connections),
            "channels": {
                channel: len(sockets)
                for channel, sockets in self.channels.items()
            },
        }


# Global manager instance
manager = ConnectionManager()
