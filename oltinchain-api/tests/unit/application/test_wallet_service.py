"""Unit tests for WalletService."""

from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.wallet_service import WalletService
from app.infrastructure.models import Balance, Order


class TestWalletServiceGetBalances:
    """Tests for get_balances method."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return WalletService(mock_session)

    @pytest.mark.asyncio
    async def test_get_balances_returns_both_assets(self, service, mock_session):
        """Test that both UZS and OLTIN balances are returned."""
        user_id = uuid4()
        
        # Mock balances
        uzs_balance = MagicMock(spec=Balance)
        uzs_balance.asset = "UZS"
        uzs_balance.available = Decimal("100000")
        uzs_balance.locked = Decimal("5000")

        oltin_balance = MagicMock(spec=Balance)
        oltin_balance.asset = "OLTIN"
        oltin_balance.available = Decimal("0.5")
        oltin_balance.locked = Decimal("0.1")

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [uzs_balance, oltin_balance]
        mock_session.execute.return_value = result_mock

        balances = await service.get_balances(user_id)

        assert "UZS" in balances
        assert "OLTIN" in balances
        assert balances["UZS"]["available"] == Decimal("100000")
        assert balances["UZS"]["locked"] == Decimal("5000")
        assert balances["OLTIN"]["available"] == Decimal("0.5")
        assert balances["OLTIN"]["locked"] == Decimal("0.1")

    @pytest.mark.asyncio
    async def test_get_balances_empty_returns_zeros(self, service, mock_session):
        """Test empty balances return zeros."""
        user_id = uuid4()
        
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        balances = await service.get_balances(user_id)

        assert balances["UZS"]["available"] == Decimal("0")
        assert balances["UZS"]["locked"] == Decimal("0")
        assert balances["OLTIN"]["available"] == Decimal("0")
        assert balances["OLTIN"]["locked"] == Decimal("0")


class TestWalletServiceGetTransactions:
    """Tests for get_transactions_from_orders method."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return WalletService(mock_session)

    @pytest.mark.asyncio
    async def test_get_transactions_returns_orders(self, service, mock_session):
        """Test that completed orders are returned."""
        user_id = uuid4()
        
        order = MagicMock(spec=Order)
        order.id = uuid4()
        order.type = "buy"
        order.status = "completed"
        order.amount_uzs = Decimal("100000")
        order.amount_oltin = Decimal("0.15")

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [order]
        mock_session.execute.return_value = result_mock

        orders = await service.get_transactions_from_orders(user_id, limit=50, offset=0)

        assert len(orders) == 1
        assert orders[0].type == "buy"

    @pytest.mark.asyncio
    async def test_get_transactions_empty(self, service, mock_session):
        """Test empty transactions."""
        user_id = uuid4()
        
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        orders = await service.get_transactions_from_orders(user_id, limit=10, offset=5)

        assert len(orders) == 0
        mock_session.execute.assert_called_once()


class TestWalletServiceSyncBlockchain:
    """Tests for sync_blockchain_balance method."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return WalletService(mock_session)

    @pytest.mark.asyncio
    async def test_sync_success_when_balanced(self, service, mock_session):
        """Test sync returns is_synced=True when balances match."""
        user_id = uuid4()
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # Mock local balance
        local_balance = MagicMock(spec=Balance)
        local_balance.available = Decimal("1.0")
        local_balance.locked = Decimal("0.0")

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = local_balance
        mock_session.execute.return_value = result_mock

        # Mock blockchain client
        with patch("app.application.services.wallet_service.ZkSyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get_balance = AsyncMock(return_value=Decimal("1.0"))
            MockClient.return_value = mock_client

            result = await service.sync_blockchain_balance(user_id, wallet_address)

            assert result["is_synced"] is True
            assert result["wallet_address"] == wallet_address
            assert result["on_chain_balance"] == Decimal("1.0")
            assert result["local_total"] == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_sync_detects_discrepancy(self, service, mock_session):
        """Test sync detects when balances dont match."""
        user_id = uuid4()
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # Mock local balance
        local_balance = MagicMock(spec=Balance)
        local_balance.available = Decimal("1.0")
        local_balance.locked = Decimal("0.0")

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = local_balance
        mock_session.execute.return_value = result_mock

        # Mock blockchain returning different balance
        with patch("app.application.services.wallet_service.ZkSyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get_balance = AsyncMock(return_value=Decimal("2.5"))
            MockClient.return_value = mock_client

            result = await service.sync_blockchain_balance(user_id, wallet_address)

            assert result["is_synced"] is False
            assert result["discrepancy"] == Decimal("1.5")

    @pytest.mark.asyncio
    async def test_sync_handles_blockchain_error(self, service, mock_session):
        """Test sync handles blockchain errors gracefully."""
        user_id = uuid4()
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        from app.domain.exceptions import BlockchainError

        with patch("app.application.services.wallet_service.ZkSyncClient") as MockClient:
            MockClient.side_effect = BlockchainError("Connection failed")

            result = await service.sync_blockchain_balance(user_id, wallet_address)

            assert result["is_synced"] is False
            assert "error" in result
