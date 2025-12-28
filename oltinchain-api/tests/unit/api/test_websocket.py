"""Unit tests for WebSocket components."""

from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.ws.manager import ConnectionManager


class TestConnectionManager:
    """Tests for ConnectionManager."""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_connect_adds_to_all_connections(self, manager):
        """Test that connect adds websocket to all_connections."""
        mock_ws = AsyncMock()
        
        await manager.connect(mock_ws)
        
        assert mock_ws in manager.all_connections
        mock_ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_user_id(self, manager):
        """Test that connect with user_id creates user mapping."""
        mock_ws = AsyncMock()
        user_id = uuid4()
        
        await manager.connect(mock_ws, user_id=user_id)
        
        assert str(user_id) in manager.active_connections
        assert mock_ws in manager.active_connections[str(user_id)]

    @pytest.mark.asyncio
    async def test_connect_with_channels(self, manager):
        """Test that connect subscribes to channels."""
        mock_ws = AsyncMock()
        channels = ["price", "metrics"]
        
        await manager.connect(mock_ws, channels=channels)
        
        assert mock_ws in manager.channels["price"]
        assert mock_ws in manager.channels["metrics"]

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager):
        """Test that disconnect removes websocket."""
        mock_ws = AsyncMock()
        user_id = uuid4()
        
        await manager.connect(mock_ws, user_id=user_id, channels=["price"])
        await manager.disconnect(mock_ws, user_id=user_id)
        
        assert mock_ws not in manager.all_connections
        assert str(user_id) not in manager.active_connections
        assert mock_ws not in manager.channels["price"]

    @pytest.mark.asyncio
    async def test_send_personal(self, manager):
        """Test sending message to specific user."""
        mock_ws = AsyncMock()
        user_id = uuid4()
        
        await manager.connect(mock_ws, user_id=user_id)
        await manager.send_personal(user_id, {"type": "test"})
        
        mock_ws.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting to all connections."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        await manager.broadcast({"type": "test"})
        
        mock_ws1.send_text.assert_called()
        mock_ws2.send_text.assert_called()

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, manager):
        """Test broadcasting to specific channel."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws3 = AsyncMock()
        
        await manager.connect(mock_ws1, channels=["price"])
        await manager.connect(mock_ws2, channels=["price"])
        await manager.connect(mock_ws3, channels=["metrics"])
        
        await manager.broadcast_to_channel("price", {"type": "price_update"})
        
        mock_ws1.send_text.assert_called()
        mock_ws2.send_text.assert_called()
        mock_ws3.send_text.assert_not_called()

    def test_get_stats(self, manager):
        """Test get_stats returns correct counts."""
        stats = manager.get_stats()
        
        assert "total_connections" in stats
        assert "users_connected" in stats
        assert "channels" in stats
        assert stats["total_connections"] == 0
