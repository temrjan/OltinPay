"""WebSocket endpoint."""

import json
from uuid import UUID

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError

from app.config import settings
from app.api.ws.manager import manager

logger = structlog.get_logger()

router = APIRouter()


def verify_ws_token(token: str) -> UUID | None:
    """Verify JWT token and return user_id."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        return UUID(user_id) if user_id else None
    except (JWTError, ValueError):
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=None),
    channels: str = Query(default="price,metrics"),
):
    """
    WebSocket endpoint for real-time updates.
    
    Query params:
        token: JWT access token (optional for public channels)
        channels: Comma-separated list of channels (price, transactions, metrics)
    
    Channels:
        - price: Gold price updates (public)
        - metrics: System metrics (public)
        - transactions: User transaction updates (requires auth)
    """
    user_id = None
    channel_list = [c.strip() for c in channels.split(",") if c.strip()]

    # Auth for private channels
    if "transactions" in channel_list:
        if not token:
            await websocket.close(code=4001, reason="Token required for transactions")
            return
        user_id = verify_ws_token(token)
        if not user_id:
            await websocket.close(code=4002, reason="Invalid token")
            return

    try:
        await manager.connect(websocket, user_id, channel_list)

        # Send initial message
        await websocket.send_json({
            "type": "connected",
            "channels": channel_list,
            "authenticated": user_id is not None,
        })

        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle ping
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                # Handle subscribe/unsubscribe
                elif message.get("type") == "subscribe":
                    channel = message.get("channel")
                    if channel in manager.channels:
                        if channel == "transactions" and not user_id:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Auth required for transactions",
                            })
                        else:
                            manager.channels[channel].add(websocket)
                            await websocket.send_json({
                                "type": "subscribed",
                                "channel": channel,
                            })

                elif message.get("type") == "unsubscribe":
                    channel = message.get("channel")
                    if channel in manager.channels:
                        manager.channels[channel].discard(websocket)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "channel": channel,
                        })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error("websocket_error", error=str(e))
        await manager.disconnect(websocket, user_id)


@router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics."""
    return manager.get_stats()
