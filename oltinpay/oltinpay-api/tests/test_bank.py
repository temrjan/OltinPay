"""Bank connector tests — HMAC auth + A2 idempotency + on-chain routing.

The SignerPool send is patched at src.bank.service.send_via (welcome-test
template). A2 idempotency is exercised sequentially: first call 200, duplicate
idempotency key 409, and exactly ONE on-chain write. Dropping the UNIQUE
constraint makes the duplicate insert succeed -> two writes -> these tests fail
(red mutation).
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient
from jose import jwt
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 — runtime type for fixtures
)

from src.bank import service as bank_service
from src.bank.deps import compute_signature
from src.bank.models import BankDeposit, ReserveAttestation
from src.config import settings
from src.infrastructure.signer_pool import Role, SignerError
from src.users.models import User
from src.withdrawals import service as withdrawals_service

SECRET = "test-bank-hmac-secret"
FAKE_TX = "0x" + "e" * 64
WALLET = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"

MINT_SELECTOR = "0x40c10f19"
ADMIN_BURN_SELECTOR = "0x06dd0419"
POST_ANSWER_SELECTOR = "0xd7fc7b18"


@pytest.fixture(autouse=True)
def _bank_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "bank_hmac_secret", SecretStr(SECRET))


def _signer_mock() -> Any:
    return patch("src.bank.service.send_via", new=AsyncMock(return_value=FAKE_TX))


def _headers(
    body: bytes,
    *,
    nonce: str | None = None,
    ts: str | None = None,
    secret: str = SECRET,
) -> dict[str, str]:
    ts = ts or str(int(time.time()))
    nonce = nonce or str(uuid.uuid4())
    return {
        "X-Bank-Signature": compute_signature(secret, body, ts, nonce),
        "X-Bank-Timestamp": ts,
        "X-Bank-Nonce": nonce,
        "Content-Type": "application/json",
    }


async def _bank_post(
    client: AsyncClient, url: str, payload: dict[str, Any] | None = None, **hdr: Any
) -> httpx.Response:
    body = b"" if payload is None else json.dumps(payload).encode()
    return await client.post(url, content=body, headers=_headers(body, **hdr))


async def _bank_get(client: AsyncClient, url: str) -> httpx.Response:
    return await client.get(url, headers=_headers(b""))


def _uint256(n: int) -> str:
    return f"{n & (2**256 - 1):064x}"


def _round_data(answer: int, updated_at: int) -> dict[str, object]:
    body = (
        _uint256(1) + _uint256(answer) + _uint256(0) + _uint256(updated_at) + _uint256(1)
    )
    return {"jsonrpc": "2.0", "id": 1, "result": "0x" + body}


def _token(user_id: uuid.UUID) -> str:
    return jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(UTC) + timedelta(minutes=30), "type": "access"},
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


@pytest_asyncio.fixture
async def wallet_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        telegram_id=71_000,
        oltin_id="bankuser",
        language="en",
        wallet_address=WALLET.lower(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _seed_deposit(db: AsyncSession, user_id: uuid.UUID, amount_uzs: int) -> None:
    """Give the user a confirmed bank deposit so withdrawals stay within the
    deposit-backed solvency cap (see the withdrawals.service SECURITY note)."""
    db.add(
        BankDeposit(
            id=uuid.uuid4(),
            user_id=user_id,
            bank_tx_id=f"SEED-{uuid.uuid4()}",
            amount_uzs=amount_uzs,
            amount_wei=str(amount_uzs * 10**18),
            tx_hash="0x" + "c" * 64,
        )
    )
    await db.commit()


# --------------------------------------------------------------------------- #
# HMAC auth                                                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_missing_headers_rejected(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/bank/fx", content=b"{}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_signature_rejected(client: AsyncClient) -> None:
    body = json.dumps({"uzsPerUsd": 12500, "source": "CBU"}).encode()
    headers = _headers(body)
    headers["X-Bank-Signature"] = "deadbeef"
    resp = await client.post("/api/v1/bank/fx", content=body, headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_stale_timestamp_rejected(client: AsyncClient) -> None:
    old_ts = str(int(time.time()) - 10_000)
    resp = await _bank_post(
        client, "/api/v1/bank/fx", {"uzsPerUsd": 12500, "source": "CBU"}, ts=old_ts
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_replayed_nonce_rejected(client: AsyncClient) -> None:
    body = json.dumps({"uzsPerUsd": 12500, "source": "CBU"}).encode()
    nonce = str(uuid.uuid4())
    ts = str(int(time.time()))
    headers = _headers(body, nonce=nonce, ts=ts)
    with _signer_mock():
        first = await client.post("/api/v1/bank/fx", content=body, headers=headers)
        second = await client.post("/api/v1/bank/fx", content=body, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 401  # nonce replay


@pytest.mark.asyncio
async def test_unconfigured_secret_returns_503(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "bank_hmac_secret", None)
    resp = await client.post("/api/v1/bank/fx", content=b"{}")
    assert resp.status_code == 503


# --------------------------------------------------------------------------- #
# attestations                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_attestation_posts_and_idempotent(client: AsyncClient) -> None:
    with _signer_mock() as mock_send:
        first = await _bank_post(
            client, "/api/v1/bank/attestations", {"grams": 1000, "auditRef": "AUD-1"}
        )
        second = await _bank_post(
            client, "/api/v1/bank/attestations", {"grams": 1000, "auditRef": "AUD-1"}
        )

    assert first.status_code == 200
    assert first.json()["txHash"] == FAKE_TX
    assert second.status_code == 409  # duplicate auditRef
    assert mock_send.call_count == 1  # only ONE on-chain postAnswer
    role, contract, calldata = mock_send.call_args.args
    assert role is Role.RESERVE
    assert contract == settings.reserve_attestor_address
    assert calldata.startswith(POST_ANSWER_SELECTOR)


@pytest.mark.asyncio
async def test_attestations_latest(client: AsyncClient) -> None:
    with _signer_mock():
        await _bank_post(
            client, "/api/v1/bank/attestations", {"grams": 1000, "auditRef": "LAT-1"}
        )
    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(
            side_effect=[httpx.Response(200, json=_round_data(1000 * 10**8, 1_800_000_000))]
        )
        resp = await _bank_get(client, "/api/v1/bank/attestations/latest")

    assert resp.status_code == 200
    body = resp.json()
    assert body["latest"]["auditRef"] == "LAT-1"
    assert body["onchainAnswer"] == str(1000 * 10**8)
    assert body["onchainUpdatedAt"] == 1_800_000_000


# --------------------------------------------------------------------------- #
# fx                                                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_fx_posts_uzs_rate(client: AsyncClient) -> None:
    with _signer_mock() as mock_send:
        resp = await _bank_post(
            client, "/api/v1/bank/fx", {"uzsPerUsd": 12500, "source": "CBU"}
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == str(round(10**8 / 12500))  # USD per UZS * 1e8
    assert body["decimals"] == 8
    role, contract, calldata = mock_send.call_args.args
    assert role is Role.UZS
    assert contract == settings.uzs_feed_address
    assert calldata.startswith(POST_ANSWER_SELECTOR)


@pytest.mark.asyncio
async def test_fx_rejects_both_rates(client: AsyncClient) -> None:
    resp = await _bank_post(
        client,
        "/api/v1/bank/fx",
        {"uzsPerUsd": 12500, "usdPerUzs": 0.00008, "source": "CBU"},
    )
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# deposits                                                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_deposit_mints_uzd(client: AsyncClient, wallet_user: User) -> None:
    with _signer_mock() as mock_send:
        resp = await _bank_post(
            client,
            "/api/v1/bank/deposits",
            {"userId": str(wallet_user.id), "amountUzs": 5000, "bankTxId": "BTX-1"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["amountWei"] == str(5000 * 10**18)
    assert body["txHash"] == FAKE_TX
    role, contract, calldata = mock_send.call_args.args
    assert role is Role.BANK_OPS
    assert contract == settings.uzd_contract_address
    assert calldata.startswith(MINT_SELECTOR)


@pytest.mark.asyncio
@pytest.mark.usefixtures("wallet_user")
async def test_deposit_by_oltin_id(client: AsyncClient) -> None:
    with _signer_mock() as mock_send:
        resp = await _bank_post(
            client,
            "/api/v1/bank/deposits",
            {"oltinId": "bankuser", "amountUzs": 100, "bankTxId": "BTX-OID"},
        )
    assert resp.status_code == 200
    assert mock_send.call_count == 1


@pytest.mark.asyncio
async def test_deposit_idempotent_bank_tx_id(
    client: AsyncClient, wallet_user: User
) -> None:
    payload = {"userId": str(wallet_user.id), "amountUzs": 5000, "bankTxId": "BTX-DUP"}
    with _signer_mock() as mock_send:
        first = await _bank_post(client, "/api/v1/bank/deposits", payload)
        second = await _bank_post(client, "/api/v1/bank/deposits", payload)
    assert first.status_code == 200
    assert second.status_code == 409  # duplicate bankTxId
    assert mock_send.call_count == 1  # minted exactly once


@pytest.mark.asyncio
async def test_deposit_unknown_user(client: AsyncClient) -> None:
    with _signer_mock() as mock_send:
        resp = await _bank_post(
            client,
            "/api/v1/bank/deposits",
            {"userId": str(uuid.uuid4()), "amountUzs": 100, "bankTxId": "BTX-X"},
        )
    assert resp.status_code == 404
    mock_send.assert_not_called()


# --------------------------------------------------------------------------- #
# withdrawals (bank side, HTTP)                                                #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_confirm_and_list_withdrawal(
    client: AsyncClient, wallet_user: User, db_session: AsyncSession
) -> None:
    await _seed_deposit(db_session, wallet_user.id, 1_000_000)
    withdrawal = await withdrawals_service.create_withdrawal(db_session, wallet_user, 5000)
    await db_session.commit()

    listed = await _bank_get(client, "/api/v1/bank/withdrawals?status=pending")
    assert listed.status_code == 200
    assert any(w["id"] == str(withdrawal.id) for w in listed.json())

    with _signer_mock() as mock_send:
        resp = await _bank_post(
            client, f"/api/v1/bank/withdrawals/{withdrawal.id}/confirm"
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "confirmed"
    assert body["txHash"] == FAKE_TX
    _role, _contract, calldata = mock_send.call_args.args
    assert calldata.startswith(ADMIN_BURN_SELECTOR)


@pytest.mark.asyncio
async def test_confirm_no_double_burn(
    client: AsyncClient, wallet_user: User, db_session: AsyncSession
) -> None:
    await _seed_deposit(db_session, wallet_user.id, 1_000_000)
    withdrawal = await withdrawals_service.create_withdrawal(db_session, wallet_user, 5000)
    await db_session.commit()

    with _signer_mock() as mock_send:
        first = await _bank_post(
            client, f"/api/v1/bank/withdrawals/{withdrawal.id}/confirm"
        )
        second = await _bank_post(
            client, f"/api/v1/bank/withdrawals/{withdrawal.id}/confirm"
        )
    assert first.status_code == 200
    assert second.status_code == 409
    assert mock_send.call_count == 1


@pytest.mark.asyncio
async def test_reject_withdrawal(
    client: AsyncClient, wallet_user: User, db_session: AsyncSession
) -> None:
    await _seed_deposit(db_session, wallet_user.id, 1_000_000)
    withdrawal = await withdrawals_service.create_withdrawal(db_session, wallet_user, 5000)
    await db_session.commit()

    with _signer_mock() as mock_send:
        resp = await _bank_post(
            client, f"/api/v1/bank/withdrawals/{withdrawal.id}/reject"
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    mock_send.assert_not_called()


# --------------------------------------------------------------------------- #
# A2 rollback-on-broadcast-failure (no orphan row pins the idempotency key)     #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_deposit_rolls_back_on_broadcast_failure(
    wallet_user: User, db_session: AsyncSession
) -> None:
    """If the on-chain mint fails AFTER the reservation insert, the row is rolled
    back so the same bankTxId can be retried (no orphan pinning the key)."""
    user_id = wallet_user.id  # capture before any rollback expires the instance

    with (
        patch(
            "src.bank.service.send_via",
            new=AsyncMock(side_effect=SignerError("broadcast failed")),
        ),
        pytest.raises(SignerError),
    ):
        await bank_service.create_deposit(
            db_session,
            user_id=user_id,
            oltin_id=None,
            amount_uzs=5000,
            bank_tx_id="BTX-FAIL",
        )

    count = (
        await db_session.execute(
            select(func.count())
            .select_from(BankDeposit)
            .where(BankDeposit.bank_tx_id == "BTX-FAIL")
        )
    ).scalar_one()
    assert count == 0  # reservation rolled back, idempotency key not orphaned

    with patch("src.bank.service.send_via", new=AsyncMock(return_value=FAKE_TX)):
        row = await bank_service.create_deposit(
            db_session,
            user_id=user_id,
            oltin_id=None,
            amount_uzs=5000,
            bank_tx_id="BTX-FAIL",
        )
    assert row.tx_hash == FAKE_TX  # retry with the same key now succeeds


@pytest.mark.asyncio
async def test_attestation_rolls_back_on_broadcast_failure(
    db_session: AsyncSession,
) -> None:
    """Same rollback-on-broadcast-failure guarantee for attestations."""
    with (
        patch(
            "src.bank.service.send_via",
            new=AsyncMock(side_effect=SignerError("broadcast failed")),
        ),
        pytest.raises(SignerError),
    ):
        await bank_service.post_attestation(db_session, 1000, "AUD-FAIL")

    count = (
        await db_session.execute(
            select(func.count())
            .select_from(ReserveAttestation)
            .where(ReserveAttestation.audit_ref == "AUD-FAIL")
        )
    ).scalar_one()
    assert count == 0

    with patch("src.bank.service.send_via", new=AsyncMock(return_value=FAKE_TX)):
        row = await bank_service.post_attestation(db_session, 1000, "AUD-FAIL")
    assert row.tx_hash == FAKE_TX
