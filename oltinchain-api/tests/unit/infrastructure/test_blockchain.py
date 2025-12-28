"""Unit tests for blockchain client."""

from decimal import Decimal

import pytest

from app.infrastructure.blockchain.zksync_client import ZkSyncClient


class TestZkSyncClientConversions:
    """Tests for wei/grams conversions."""

    def test_to_wei_whole_number(self):
        # Arrange
        client = object.__new__(ZkSyncClient)  # Create without __init__

        # Act
        result = client._to_wei(Decimal("1"))

        # Assert
        assert result == 10**18

    def test_to_wei_fractional(self):
        # Arrange
        client = object.__new__(ZkSyncClient)

        # Act
        result = client._to_wei(Decimal("1.5"))

        # Assert
        assert result == 1_500_000_000_000_000_000

    def test_to_wei_small_amount(self):
        # Arrange
        client = object.__new__(ZkSyncClient)

        # Act
        result = client._to_wei(Decimal("0.001"))

        # Assert
        assert result == 1_000_000_000_000_000

    def test_from_wei_whole_number(self):
        # Arrange
        client = object.__new__(ZkSyncClient)

        # Act
        result = client._from_wei(10**18)

        # Assert
        assert result == Decimal("1")

    def test_from_wei_fractional(self):
        # Arrange
        client = object.__new__(ZkSyncClient)

        # Act
        result = client._from_wei(1_500_000_000_000_000_000)

        # Assert
        assert result == Decimal("1.5")

    def test_roundtrip_conversion(self):
        # Arrange
        client = object.__new__(ZkSyncClient)
        original = Decimal("123.456789012345678901")

        # Act
        wei = client._to_wei(original)
        back = client._from_wei(wei)

        # Assert - should preserve 18 decimal places
        assert str(back)[:20] == str(original)[:20]
