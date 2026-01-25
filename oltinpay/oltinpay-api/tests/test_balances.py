"""Balances module tests."""

import pytest
from httpx import AsyncClient


class TestGetBalances:
    """Tests for getting balances."""

    @pytest.mark.asyncio
    async def test_get_balances(self, client: AsyncClient, test_user):
        """Test getting all user balances."""
        response = await client.get(
            "/api/v1/balances",
            headers=test_user["headers"],
        )

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "total_usd" in data
        assert "wallet" in data
        assert "exchange" in data
        assert "staking" in data

        # Check wallet has both currencies
        assert "usd" in data["wallet"]
        assert "oltin" in data["wallet"]

    @pytest.mark.asyncio
    async def test_get_balances_unauthorized(self, client: AsyncClient):
        """Test getting balances without auth fails."""
        response = await client.get("/api/v1/balances")

        assert response.status_code == 401


class TestInternalTransfer:
    """Tests for internal transfers between own accounts."""

    @pytest.mark.asyncio
    async def test_transfer_wallet_to_exchange(self, client: AsyncClient, test_user):
        """Test transferring from wallet to exchange."""
        response = await client.post(
            "/api/v1/balances/transfer",
            headers=test_user["headers"],
            json={
                "from_account": "wallet",
                "to_account": "exchange",
                "currency": "USD",
                "amount": "10.00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["from_account"] == "wallet"
        assert data["to_account"] == "exchange"

    @pytest.mark.asyncio
    async def test_transfer_insufficient_balance(self, client: AsyncClient, test_user):
        """Test transfer with insufficient balance fails."""
        response = await client.post(
            "/api/v1/balances/transfer",
            headers=test_user["headers"],
            json={
                "from_account": "wallet",
                "to_account": "exchange",
                "currency": "USD",
                "amount": "99999.00",
            },
        )

        assert response.status_code == 400
        assert "Insufficient" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_transfer_exchange_to_staking_oltin(
        self, client: AsyncClient, test_user
    ):
        """Test transferring OLTIN from exchange to staking."""
        response = await client.post(
            "/api/v1/balances/transfer",
            headers=test_user["headers"],
            json={
                "from_account": "exchange",
                "to_account": "staking",
                "currency": "OLTIN",
                "amount": "1.0",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_transfer_staking_usd_fails(self, client: AsyncClient, test_user):
        """Test transferring USD to staking fails (only OLTIN allowed)."""
        response = await client.post(
            "/api/v1/balances/transfer",
            headers=test_user["headers"],
            json={
                "from_account": "wallet",
                "to_account": "staking",
                "currency": "USD",
                "amount": "10.00",
            },
        )

        assert response.status_code == 400
        assert "OLTIN" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_transfer_invalid_account(self, client: AsyncClient, test_user):
        """Test transfer with invalid account name fails."""
        response = await client.post(
            "/api/v1/balances/transfer",
            headers=test_user["headers"],
            json={
                "from_account": "invalid",
                "to_account": "exchange",
                "currency": "USD",
                "amount": "10.00",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_transfer_negative_amount(self, client: AsyncClient, test_user):
        """Test transfer with negative amount fails."""
        response = await client.post(
            "/api/v1/balances/transfer",
            headers=test_user["headers"],
            json={
                "from_account": "wallet",
                "to_account": "exchange",
                "currency": "USD",
                "amount": "-10.00",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_transfer_zero_amount(self, client: AsyncClient, test_user):
        """Test transfer with zero amount fails."""
        response = await client.post(
            "/api/v1/balances/transfer",
            headers=test_user["headers"],
            json={
                "from_account": "wallet",
                "to_account": "exchange",
                "currency": "USD",
                "amount": "0",
            },
        )

        assert response.status_code == 422
