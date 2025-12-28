"""Unit tests for OrderService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.services.order_service import OrderService
from app.application.services.price_service import PriceService
from app.domain.exceptions import InsufficientBalanceError, BlockchainError
from app.infrastructure.models import Order, Balance


class TestOrderServiceBuy:
    """Tests for OrderService.buy method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.order_repo = AsyncMock()
        self.balance_repo = AsyncMock()
        self.blockchain = AsyncMock()
        self.price_service = PriceService(
            gold_price_uzs_per_gram=650_000,
            fee_percent=0.015,
            min_fee_uzs=3_800,
        )
        self.service = OrderService(
            order_repo=self.order_repo,
            balance_repo=self.balance_repo,
            blockchain=self.blockchain,
            price_service=self.price_service,
        )
        self.user_id = uuid4()
        self.wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

    @pytest.mark.asyncio
    async def test_buy_success(self):
        # Arrange
        amount_uzs = Decimal("1000000")
        tx_hash = "0xabc123"

        # Mock order creation with proper return
        async def create_order(order):
            order.id = uuid4()
            return order
        self.order_repo.create.side_effect = create_order
        self.order_repo.update.return_value = None
        self.balance_repo.lock_funds.return_value = Balance(
            user_id=self.user_id, asset="UZS", available=Decimal("0"), locked=amount_uzs
        )
        self.balance_repo.release_locked.return_value = None
        self.balance_repo.add_available.return_value = None
        self.blockchain.mint.return_value = tx_hash

        # Act
        order = await self.service.buy(self.user_id, self.wallet_address, amount_uzs)

        # Assert
        assert order.type == "buy"
        assert order.status == "completed"
        assert order.tx_hash == tx_hash
        assert order.amount_uzs == amount_uzs
        self.balance_repo.lock_funds.assert_called_once_with(self.user_id, "UZS", amount_uzs)
        self.blockchain.mint.assert_called_once()

    @pytest.mark.asyncio
    async def test_buy_insufficient_balance(self):
        # Arrange
        amount_uzs = Decimal("1000000")
        self.balance_repo.lock_funds.side_effect = InsufficientBalanceError("Not enough UZS")

        # Act & Assert
        with pytest.raises(InsufficientBalanceError):
            await self.service.buy(self.user_id, self.wallet_address, amount_uzs)

        self.order_repo.create.assert_not_called()
        self.blockchain.mint.assert_not_called()

    @pytest.mark.asyncio
    async def test_buy_blockchain_failure_unlocks_funds(self):
        # Arrange
        amount_uzs = Decimal("1000000")

        async def create_order(order):
            order.id = uuid4()
            return order
        self.order_repo.create.side_effect = create_order
        self.balance_repo.lock_funds.return_value = Balance(
            user_id=self.user_id, asset="UZS", available=Decimal("0"), locked=amount_uzs
        )
        self.blockchain.mint.side_effect = BlockchainError("Mint failed")

        # Act
        order = await self.service.buy(self.user_id, self.wallet_address, amount_uzs)

        # Assert
        assert order.status == "failed"
        assert "Mint failed" in order.error_message
        self.balance_repo.unlock_funds.assert_called_once_with(self.user_id, "UZS", amount_uzs)

    @pytest.mark.asyncio
    async def test_buy_calculates_correct_fee(self):
        # Arrange
        amount_uzs = Decimal("1000000")  # 1.5% = 15000 fee
        tx_hash = "0xabc123"

        async def create_order(order):
            order.id = uuid4()
            return order
        self.order_repo.create.side_effect = create_order
        self.balance_repo.lock_funds.return_value = None
        self.blockchain.mint.return_value = tx_hash

        # Act
        order = await self.service.buy(self.user_id, self.wallet_address, amount_uzs)

        # Assert
        assert order.fee_uzs == Decimal("15000.00")


class TestOrderServiceSell:
    """Tests for OrderService.sell method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.order_repo = AsyncMock()
        self.balance_repo = AsyncMock()
        self.blockchain = AsyncMock()
        self.price_service = PriceService(
            gold_price_uzs_per_gram=650_000,
            fee_percent=0.015,
            min_fee_uzs=3_800,
        )
        self.service = OrderService(
            order_repo=self.order_repo,
            balance_repo=self.balance_repo,
            blockchain=self.blockchain,
            price_service=self.price_service,
        )
        self.user_id = uuid4()
        self.wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

    @pytest.mark.asyncio
    async def test_sell_success(self):
        # Arrange
        amount_oltin = Decimal("1")  # 1 gram = 650000 UZS
        tx_hash = "0xdef456"

        async def create_order(order):
            order.id = uuid4()
            return order
        self.order_repo.create.side_effect = create_order
        self.balance_repo.lock_funds.return_value = None
        self.balance_repo.release_locked.return_value = None
        self.balance_repo.add_available.return_value = None
        self.blockchain.burn.return_value = tx_hash

        # Act
        order = await self.service.sell(self.user_id, self.wallet_address, amount_oltin)

        # Assert
        assert order.type == "sell"
        assert order.status == "completed"
        assert order.tx_hash == tx_hash
        assert order.amount_oltin == amount_oltin
        self.balance_repo.lock_funds.assert_called_once_with(self.user_id, "OLTIN", amount_oltin)
        self.blockchain.burn.assert_called_once()

    @pytest.mark.asyncio
    async def test_sell_insufficient_balance(self):
        # Arrange
        amount_oltin = Decimal("1")
        self.balance_repo.lock_funds.side_effect = InsufficientBalanceError("Not enough OLTIN")

        # Act & Assert
        with pytest.raises(InsufficientBalanceError):
            await self.service.sell(self.user_id, self.wallet_address, amount_oltin)

        self.order_repo.create.assert_not_called()
        self.blockchain.burn.assert_not_called()

    @pytest.mark.asyncio
    async def test_sell_blockchain_failure_unlocks_funds(self):
        # Arrange
        amount_oltin = Decimal("1")

        async def create_order(order):
            order.id = uuid4()
            return order
        self.order_repo.create.side_effect = create_order
        self.balance_repo.lock_funds.return_value = None
        self.blockchain.burn.side_effect = BlockchainError("Burn failed")

        # Act
        order = await self.service.sell(self.user_id, self.wallet_address, amount_oltin)

        # Assert
        assert order.status == "failed"
        assert "Burn failed" in order.error_message
        self.balance_repo.unlock_funds.assert_called_once_with(self.user_id, "OLTIN", amount_oltin)

    @pytest.mark.asyncio
    async def test_sell_calculates_correct_amounts(self):
        # Arrange
        amount_oltin = Decimal("1")  # 1 gram
        # 650000 UZS, fee = 9750, net = 640250
        tx_hash = "0xdef456"

        async def create_order(order):
            order.id = uuid4()
            return order
        self.order_repo.create.side_effect = create_order
        self.balance_repo.lock_funds.return_value = None
        self.blockchain.burn.return_value = tx_hash

        # Act
        order = await self.service.sell(self.user_id, self.wallet_address, amount_oltin)

        # Assert
        assert order.amount_uzs == Decimal("650000.00")
        assert order.fee_uzs == Decimal("9750.00")

        # Check add_available called with net amount
        self.balance_repo.add_available.assert_called_once()
        call_args = self.balance_repo.add_available.call_args
        assert call_args[0][2] == Decimal("640250.00")  # net_amount_uzs


class TestOrderServiceGetOrders:
    """Tests for OrderService order retrieval methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.order_repo = AsyncMock()
        self.balance_repo = AsyncMock()
        self.blockchain = AsyncMock()
        self.service = OrderService(
            order_repo=self.order_repo,
            balance_repo=self.balance_repo,
            blockchain=self.blockchain,
        )
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_get_user_orders(self):
        # Arrange
        orders = [MagicMock(), MagicMock()]
        self.order_repo.get_user_orders.return_value = orders

        # Act
        result = await self.service.get_user_orders(self.user_id, limit=10, offset=5)

        # Assert
        assert result == orders
        self.order_repo.get_user_orders.assert_called_once_with(self.user_id, 10, 5)

    @pytest.mark.asyncio
    async def test_get_order(self):
        # Arrange
        order_id = uuid4()
        order = MagicMock()
        self.order_repo.get_by_id.return_value = order

        # Act
        result = await self.service.get_order(order_id)

        # Assert
        assert result == order
        self.order_repo.get_by_id.assert_called_once_with(order_id)
