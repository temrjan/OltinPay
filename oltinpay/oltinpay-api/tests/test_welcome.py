"""Integration tests for /api/v1/welcome endpoints.

The SignerPool send helper (send_via) is patched so the tests never touch the
real RPC and never require a role key to be configured.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from eth_utils import to_checksum_address
from httpx import AsyncClient  # noqa: TC002  — runtime type for fixture
from jose import jwt
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002  — runtime type for fixture
)

from src.config import settings
from src.infrastructure.signer_pool import Role, SignerReceiptTimeout
from src.users.models import User

CLAIM = "/api/v1/welcome/claim"
STATUS = "/api/v1/welcome/status"
WALLET = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"
FAKE_TX = "0x" + "b" * 64  # the UZD mint tx in tests
DRIP_TX = "0x" + "d" * 64  # the ETH gas-drip tx in tests


@pytest.fixture(autouse=True)
def _wallet_already_funded():
    """Default: report the wallet as already funded so the gas drip is SKIPPED.

    Existing claim tests then see send_via only for the UZD mint — their
    behaviour is unchanged by the drip. Drip-specific tests override this fixture
    with a low balance (patching the same target inside their own ``with``).
    """
    with patch(
        "src.welcome.service.get_eth_balance",
        new=AsyncMock(return_value=10**16),  # 0.01 ETH, well above threshold
    ):
        yield


def _make_token(user_id: uuid.UUID) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "access",
        },
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


@pytest_asyncio.fixture
async def wallet_user(db_session: AsyncSession) -> dict[str, Any]:
    user = User(
        id=uuid.uuid4(),
        telegram_id=77_000,
        oltin_id="walletuser",
        language="en",
        wallet_address=WALLET.lower(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {"user": user, "headers": {"Authorization": f"Bearer {_make_token(user.id)}"}}


@pytest_asyncio.fixture
async def no_wallet_user(db_session: AsyncSession) -> dict[str, Any]:
    user = User(
        id=uuid.uuid4(),
        telegram_id=78_000,
        oltin_id="nowallet",
        language="en",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {"user": user, "headers": {"Authorization": f"Bearer {_make_token(user.id)}"}}


@pytest.mark.asyncio
async def test_claim_success(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    with patch(
        "src.welcome.service.send_via",
        new=AsyncMock(return_value=FAKE_TX),
    ):
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["tx_hash"] == FAKE_TX
    assert body["amount_wei"] == str(1000 * 10**18)
    assert body["wallet_address"] == WALLET.lower()


@pytest.mark.asyncio
async def test_claim_rejects_without_wallet(
    client: AsyncClient, no_wallet_user: dict[str, Any]
) -> None:
    response = await client.post(CLAIM, headers=no_wallet_user["headers"])
    assert response.status_code == 400
    assert "Wallet address" in response.json()["detail"]


@pytest.mark.asyncio
async def test_claim_idempotent_conflict(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    with patch(
        "src.welcome.service.send_via",
        new=AsyncMock(return_value=FAKE_TX),
    ):
        first = await client.post(CLAIM, headers=wallet_user["headers"])
        assert first.status_code == 200

        second = await client.post(CLAIM, headers=wallet_user["headers"])
        assert second.status_code == 409


@pytest.mark.asyncio
async def test_claim_receipt_timeout_keeps_reservation(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """A-prime: a timed-out welcome mint (outcome UNKNOWN) keeps the reserved
    user_id slot so a retry is refused (409) instead of minting a SECOND bonus
    if the timed-out tx later mines."""
    with patch(
        "src.welcome.service.send_via",
        new=AsyncMock(side_effect=SignerReceiptTimeout("no receipt", FAKE_TX)),
    ) as mock_send:
        first = await client.post(CLAIM, headers=wallet_user["headers"])
    assert first.status_code == 409
    assert "reconciliation" in first.json()["detail"]
    assert mock_send.call_count == 1

    with patch(
        "src.welcome.service.send_via",
        new=AsyncMock(return_value=FAKE_TX),
    ) as mock_retry:
        retry = await client.post(CLAIM, headers=wallet_user["headers"])
    assert retry.status_code == 409  # already claimed
    mock_retry.assert_not_called()  # no SECOND welcome mint


@pytest.mark.asyncio
async def test_claim_requires_auth(client: AsyncClient) -> None:
    response = await client.post(CLAIM)
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_status_unclaimed(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    response = await client.get(STATUS, headers=wallet_user["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["claimed"] is False
    assert body["tx_hash"] is None


@pytest.mark.asyncio
async def test_status_after_claim(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    with patch(
        "src.welcome.service.send_via",
        new=AsyncMock(return_value=FAKE_TX),
    ):
        await client.post(CLAIM, headers=wallet_user["headers"])

    response = await client.get(STATUS, headers=wallet_user["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["claimed"] is True
    assert body["tx_hash"] == FAKE_TX


@pytest.mark.asyncio
async def test_claim_drips_gas_when_wallet_below_threshold(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """A wallet below the ETH threshold gets a native drip BEFORE the UZD mint:
    two send_via calls — the ETH value transfer first, then the mint."""
    with (
        patch(
            "src.welcome.service.get_eth_balance",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "src.welcome.service.send_via",
            new=AsyncMock(side_effect=[DRIP_TX, FAKE_TX]),
        ) as mock_send,
    ):
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    assert response.json()["tx_hash"] == FAKE_TX  # the UZD mint, not the drip
    assert mock_send.call_count == 2
    drip_call, mint_call = mock_send.call_args_list
    # Drip leg: native ETH transfer to the (checksummed) wallet, value=drip_eth_wei.
    assert drip_call.args[0] == Role.BANK_OPS
    assert drip_call.args[1] == to_checksum_address(WALLET.lower())
    assert drip_call.args[2] == "0x"
    assert drip_call.kwargs["value"] == settings.drip_eth_wei
    # Mint leg: the UZD contract (calldata call), no ETH value.
    assert mint_call.args[1] == settings.uzd_contract_address
    assert "value" not in mint_call.kwargs


@pytest.mark.asyncio
async def test_claim_succeeds_when_gas_drip_fails(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """A drip failure (bank-ops out of ETH / timeout) must NOT abort the claim —
    the UZD mint still lands and the user gets 200 (best-effort gas drip)."""
    with (
        patch(
            "src.welcome.service.get_eth_balance",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "src.welcome.service.send_via",
            new=AsyncMock(side_effect=[SignerReceiptTimeout("drip", DRIP_TX), FAKE_TX]),
        ) as mock_send,
    ):
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    assert response.json()["tx_hash"] == FAKE_TX
    assert mock_send.call_count == 2  # drip attempted (failed), then mint succeeded


@pytest.mark.asyncio
async def test_claim_skips_drip_when_wallet_already_funded(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """A wallet already at/above the threshold gets NO drip — the live balance is
    the idempotency gate, so send_via fires once (the mint) only."""
    with (
        patch(
            "src.welcome.service.get_eth_balance",
            new=AsyncMock(return_value=settings.drip_eth_threshold_wei),
        ),
        patch(
            "src.welcome.service.send_via",
            new=AsyncMock(return_value=FAKE_TX),
        ) as mock_send,
    ):
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    assert mock_send.call_count == 1  # mint only — drip gated off by the balance
