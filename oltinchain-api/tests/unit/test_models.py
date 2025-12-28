import pytest
from decimal import Decimal
from uuid import uuid4

from app.infrastructure.models import User, Balance, Order, GoldBar, Alert


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self):
        """Test user can be created with required fields."""
        user = User(
            phone="+998901234567",
            password_hash="hashed_password",
            kyc_level=0,  # Explicitly set
            is_active=True  # Explicitly set
        )
        assert user.phone == "+998901234567"
        assert user.kyc_level == 0
        assert user.is_active is True

    def test_user_with_wallet(self):
        """Test user with wallet address."""
        user = User(
            phone="+998901234567",
            password_hash="hashed_password",
            wallet_address="0x1234567890abcdef1234567890abcdef12345678"
        )
        assert user.wallet_address is not None
        assert len(user.wallet_address) == 42


class TestBalanceModel:
    """Tests for Balance model."""

    def test_balance_creation(self):
        """Test balance can be created."""
        balance = Balance(
            user_id=uuid4(),
            asset="UZS",
            available=Decimal("1000000.00"),
            locked=Decimal("0.00")
        )
        assert balance.asset == "UZS"
        assert balance.available == Decimal("1000000.00")

    def test_oltin_balance(self):
        """Test OLTIN balance with high precision."""
        balance = Balance(
            user_id=uuid4(),
            asset="OLTIN",
            available=Decimal("1.123456789012345678"),
            locked=Decimal("0.00")
        )
        assert balance.asset == "OLTIN"


class TestOrderModel:
    """Tests for Order model."""

    def test_buy_order_creation(self):
        """Test buy order creation."""
        order = Order(
            user_id=uuid4(),
            type="buy",
            status="pending",
            amount_uzs=Decimal("650000.00"),
            amount_oltin=Decimal("1.0"),
            price_per_gram=Decimal("650000.00"),
            fee_uzs=Decimal("9750.00")
        )
        assert order.type == "buy"
        assert order.status == "pending"

    def test_sell_order_creation(self):
        """Test sell order creation."""
        order = Order(
            user_id=uuid4(),
            type="sell",
            status="completed",
            amount_uzs=Decimal("650000.00"),
            amount_oltin=Decimal("1.0"),
            price_per_gram=Decimal("650000.00"),
            fee_uzs=Decimal("9750.00"),
            tx_hash="0x1234567890abcdef"
        )
        assert order.type == "sell"
        assert order.status == "completed"
        assert order.tx_hash is not None


class TestGoldBarModel:
    """Tests for GoldBar model."""

    def test_gold_bar_creation(self):
        """Test gold bar creation."""
        bar = GoldBar(
            serial_number="GB-2025-001",
            weight_grams=Decimal("1000.0000"),
            purity=Decimal("999.9"),
            vault_location="Tashkent Vault",
            status="active"  # Explicitly set
        )
        assert bar.serial_number == "GB-2025-001"
        assert bar.weight_grams == Decimal("1000.0000")
        assert bar.status == "active"


class TestAlertModel:
    """Tests for Alert model."""

    def test_alert_creation(self):
        """Test alert creation."""
        alert = Alert(
            user_id=uuid4(),
            alert_type="large_tx",
            severity="high",
            details={"amount": 10000000},
            status="new"  # Explicitly set
        )
        assert alert.alert_type == "large_tx"
        assert alert.severity == "high"
        assert alert.status == "new"
