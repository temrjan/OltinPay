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
from httpx import AsyncClient, ConnectError
from jose import jwt
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002  — runtime type for fixture
)

from src.config import settings
from src.infrastructure.signer_pool import Role, SignerError, SignerReceiptTimeout
from src.users.models import User

CLAIM = "/api/v1/welcome/claim"
STATUS = "/api/v1/welcome/status"
WALLET = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"
FAKE_TX = "0x" + "b" * 64  # the UZD mint tx in tests
DRIP_TX = "0x" + "d" * 64  # the ETH gas-drip tx in tests
OLTIN_TX = "0x" + "c" * 64  # the OLTIN transfer tx in tests


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
    assert body["tx_hash"] == FAKE_TX  # the UZD mint tx (OLTIN leg is a side-leg)
    assert body["amount_wei"] == str(settings.welcome_uzd_wei)
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
    """A wallet below the ETH threshold gets all three legs in order:
    ETH drip (before the reservation) → UZD mint → OLTIN transfer."""
    with (
        patch(
            "src.welcome.service.get_eth_balance",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "src.welcome.service.send_via",
            new=AsyncMock(side_effect=[DRIP_TX, FAKE_TX, OLTIN_TX]),
        ) as mock_send,
    ):
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    assert response.json()["tx_hash"] == FAKE_TX  # the UZD mint, not drip/oltin
    assert mock_send.call_count == 3
    drip_call, mint_call, oltin_call = mock_send.call_args_list
    # Drip leg: native ETH transfer to the (checksummed) wallet, value=drip_eth_wei.
    assert drip_call.args[0] == Role.BANK_OPS
    assert drip_call.args[1] == to_checksum_address(WALLET.lower())
    assert drip_call.args[2] == "0x"
    assert drip_call.kwargs["value"] == settings.drip_eth_wei
    # Mint leg: the UZD contract (calldata call), no ETH value.
    assert mint_call.args[1] == settings.uzd_contract_address
    assert "value" not in mint_call.kwargs
    # OLTIN leg: the OLTIN contract (ERC20 transfer calldata), no ETH value.
    assert oltin_call.args[0] == Role.BANK_OPS
    assert oltin_call.args[1] == settings.oltin_contract_address
    assert "value" not in oltin_call.kwargs


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
            new=AsyncMock(
                side_effect=[SignerReceiptTimeout("drip", DRIP_TX), FAKE_TX, OLTIN_TX]
            ),
        ) as mock_send,
    ):
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    assert response.json()["tx_hash"] == FAKE_TX
    assert mock_send.call_count == 3  # drip (failed) + mint + oltin


@pytest.mark.asyncio
async def test_claim_skips_drip_when_wallet_already_funded(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """A wallet already at/above the threshold gets NO ETH drip — the live balance
    is the gas gate. Only the mint + OLTIN legs fire (two send_via calls)."""
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
    assert mock_send.call_count == 2  # mint + oltin — ETH drip gated off by balance


@pytest.mark.asyncio
async def test_claim_succeeds_when_oltin_transfer_fails(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """OLTIN is a best-effort leg — its failure must NOT undo the committed UZD
    mint. The user still gets UZD (+ETH) and can buy OLTIN on the exchange."""
    with patch(
        "src.welcome.service.send_via",
        # funded wallet (autouse) -> drip skipped: call 1 = mint ok, call 2 = OLTIN fails.
        new=AsyncMock(side_effect=[FAKE_TX, SignerError("oltin boom")]),
    ) as mock_send:
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    assert response.json()["tx_hash"] == FAKE_TX  # mint committed despite OLTIN fail
    assert mock_send.call_count == 2  # mint ok, OLTIN attempted then swallowed


@pytest.mark.asyncio
async def test_claim_oltin_idempotent_by_claim_row_not_balance(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """OLTIN one-time-ness is tied to the claim ROW, not the live balance: a user
    who legitimately spends the gifted OLTIN (balance 0) and re-claims gets 409 and
    NO second OLTIN transfer. A balance gate (like ETH) would re-drip forever — the
    OLTIN leg runs only AFTER the reservation, so the retry 409s before reaching it."""
    with patch(
        "src.welcome.service.send_via", new=AsyncMock(return_value=FAKE_TX)
    ):
        first = await client.post(CLAIM, headers=wallet_user["headers"])
        assert first.status_code == 200

    # The user "spent" the OLTIN, but the claim row exists — a retry must not re-send.
    with patch(
        "src.welcome.service.send_via", new=AsyncMock(return_value=FAKE_TX)
    ) as mock_retry:
        second = await client.post(CLAIM, headers=wallet_user["headers"])
    assert second.status_code == 409
    mock_retry.assert_not_called()  # neither a second mint nor a second OLTIN transfer


@pytest.mark.asyncio
async def test_claim_survives_raw_transport_error_in_oltin(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """R1 (blocking review finding): a RAW transport error from the OLTIN leg
    (httpx errors are NOT wrapped in SignerError) must NOT abort the claim. The
    UZD mint is already committed, so aborting + retry would double-mint. The
    best-effort OLTIN leg (broad except, after commit) swallows ANY exception."""
    with patch(
        "src.welcome.service.send_via",
        # funded (autouse) -> drip skipped: call 1 mint ok, call 2 OLTIN raises RAW httpx.
        new=AsyncMock(side_effect=[FAKE_TX, ConnectError("rpc down")]),
    ) as mock_send:
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200  # committed mint despite the raw transport error
    assert response.json()["tx_hash"] == FAKE_TX
    assert mock_send.call_count == 2  # mint ok, OLTIN raw-error swallowed


@pytest.mark.asyncio
async def test_claim_survives_raw_transport_error_in_balance_read(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """The gas legs are best-effort with a broad except: a RAW transport error from
    the live balance read (before the reservation) must skip the drip, not turn the
    whole 'get bonus' click into a 500 — the UZD mint + OLTIN still land."""
    with (
        patch(
            "src.welcome.service.get_eth_balance",
            new=AsyncMock(side_effect=ConnectError("rpc down")),
        ),
        patch("src.welcome.service.send_via", new=AsyncMock(return_value=FAKE_TX)) as mock_send,
    ):
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    assert mock_send.call_count == 2  # drip skipped (balance unknown), then mint + oltin


@pytest.mark.asyncio
async def test_claim_survives_raw_transport_error_in_gas_drip(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    """A RAW transport error from the ETH drip SEND (below threshold) must be
    swallowed too — the drip is best-effort and runs before the reservation."""
    with (
        patch("src.welcome.service.get_eth_balance", new=AsyncMock(return_value=0)),
        patch(
            "src.welcome.service.send_via",
            # call 1 = drip raises RAW httpx; call 2 = mint ok; call 3 = OLTIN ok.
            new=AsyncMock(side_effect=[ConnectError("rpc down"), FAKE_TX, OLTIN_TX]),
        ) as mock_send,
    ):
        response = await client.post(CLAIM, headers=wallet_user["headers"])

    assert response.status_code == 200
    assert response.json()["tx_hash"] == FAKE_TX
    assert mock_send.call_count == 3  # drip raw-error swallowed, then mint + oltin
