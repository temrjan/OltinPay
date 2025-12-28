"""Unit tests for ReservesService."""

from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.reserves_service import ReservesService
from app.infrastructure.models import GoldBar


class TestReservesServiceProofOfReserves:
    """Tests for get_proof_of_reserves method."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return ReservesService(mock_session)

    @pytest.mark.asyncio
    async def test_proof_fully_backed(self, service, mock_session):
        """Test proof when reserves are fully backed."""
        # Mock physical gold sum
        sum_result = MagicMock()
        sum_result.scalar_one_or_none.return_value = Decimal("1000")
        
        # Mock bar count
        count_result = MagicMock()
        count_result.scalar_one.return_value = 10
        
        mock_session.execute.side_effect = [sum_result, count_result]

        with patch("app.application.services.reserves_service.ZkSyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get_total_supply = AsyncMock(return_value=Decimal("1000"))
            mock_client.get_token_info = AsyncMock(return_value={
                "contract_address": "0x123"
            })
            MockClient.return_value = mock_client

            proof = await service.get_proof_of_reserves()

            assert proof["coverage"]["status"] == "fully_backed"
            assert Decimal(proof["coverage"]["ratio"]) == Decimal("1")
            assert proof["physical_gold"]["total_bars"] == 10

    @pytest.mark.asyncio
    async def test_proof_under_backed(self, service, mock_session):
        """Test proof when reserves are under backed."""
        sum_result = MagicMock()
        sum_result.scalar_one_or_none.return_value = Decimal("500")
        
        count_result = MagicMock()
        count_result.scalar_one.return_value = 5
        
        mock_session.execute.side_effect = [sum_result, count_result]

        with patch("app.application.services.reserves_service.ZkSyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get_total_supply = AsyncMock(return_value=Decimal("1000"))
            mock_client.get_token_info = AsyncMock(return_value={
                "contract_address": "0x123"
            })
            MockClient.return_value = mock_client

            proof = await service.get_proof_of_reserves()

            assert proof["coverage"]["status"] == "under_backed"
            assert Decimal(proof["coverage"]["ratio"]) == Decimal("0.5")

    @pytest.mark.asyncio
    async def test_proof_no_supply(self, service, mock_session):
        """Test proof when there is no token supply."""
        sum_result = MagicMock()
        sum_result.scalar_one_or_none.return_value = Decimal("100")
        
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        
        mock_session.execute.side_effect = [sum_result, count_result]

        with patch("app.application.services.reserves_service.ZkSyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get_total_supply = AsyncMock(return_value=Decimal("0"))
            mock_client.get_token_info = AsyncMock(return_value={
                "contract_address": "0x123"
            })
            MockClient.return_value = mock_client

            proof = await service.get_proof_of_reserves()

            assert Decimal(proof["coverage"]["ratio"]) == Decimal("1")


class TestReservesServiceLookup:
    """Tests for lookup_gold_bar method."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return ReservesService(mock_session)

    @pytest.mark.asyncio
    async def test_lookup_found(self, service, mock_session):
        """Test lookup returns gold bar when found."""
        mock_bar = MagicMock(spec=GoldBar)
        mock_bar.id = uuid4()
        mock_bar.serial_number = "GB-2024-001"
        mock_bar.weight_grams = Decimal("100")
        mock_bar.purity = Decimal("999.9")
        mock_bar.status = "active"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_bar
        mock_session.execute.return_value = result_mock

        bar = await service.lookup_gold_bar("GB-2024-001")

        assert bar is not None
        assert bar.serial_number == "GB-2024-001"

    @pytest.mark.asyncio
    async def test_lookup_not_found(self, service, mock_session):
        """Test lookup returns None when not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        bar = await service.lookup_gold_bar("INVALID-001")

        assert bar is None


class TestReservesServiceGetAllBars:
    """Tests for get_all_gold_bars method."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return ReservesService(mock_session)

    @pytest.mark.asyncio
    async def test_get_all_bars_returns_list(self, service, mock_session):
        """Test get_all_gold_bars returns list."""
        mock_bar = MagicMock(spec=GoldBar)
        mock_bar.id = uuid4()
        mock_bar.serial_number = "GB-2024-001"

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_bar]
        mock_session.execute.return_value = result_mock

        bars = await service.get_all_gold_bars(limit=50, offset=0)

        assert len(bars) == 1
        assert bars[0].serial_number == "GB-2024-001"

    @pytest.mark.asyncio
    async def test_get_all_bars_empty(self, service, mock_session):
        """Test get_all_gold_bars returns empty list."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        bars = await service.get_all_gold_bars()

        assert len(bars) == 0
