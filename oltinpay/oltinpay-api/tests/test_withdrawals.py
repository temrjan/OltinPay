"""Withdrawal tests — user create/list plus the bank two-phase lifecycle.

The bank confirm/reject transitions are tested at the service layer (patching
the SignerPool send at src.bank.service.send_via); the HTTP+HMAC surface for the
same transitions is covered in test_bank.py.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient  # noqa: TC002 — runtime type for fixtures
from jose import jwt
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 — runtime type for fixtures
)

from src.bank import service as bank_service
from src.bank.models import BankDeposit
from src.common.exceptions import BadRequestException, ConflictException
from src.config import settings
from src.infrastructure.signer_pool import Role, SignerError
from src.users.models import User
from src.withdrawals import service as withdrawals_service
from src.withdrawals.models import Withdrawal, WithdrawalStatus

WALLET = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"
FAKE_TX = "0x" + "b" * 64
ADMIN_BURN_SELECTOR = "0x06dd0419"


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


async def _make_user(db: AsyncSession, *, wallet: str | None, tg: int, oid: str) -> User:
    user = User(
        id=uuid.uuid4(),
        telegram_id=tg,
        oltin_id=oid,
        language="en",
        wallet_address=wallet.lower() if wallet else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
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


@pytest_asyncio.fixture
async def wallet_user(db_session: AsyncSession) -> dict[str, Any]:
    user = await _make_user(db_session, wallet=WALLET, tg=61_000, oid="wduser")
    await _seed_deposit(db_session, user.id, 1_000_000)
    return {"user": user, "headers": {"Authorization": f"Bearer {_make_token(user.id)}"}}


@pytest.mark.asyncio
async def test_create_withdrawal_pending(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    response = await client.post(
        "/api/v1/withdrawals",
        json={"amount_uzd": 5000},
        headers=wallet_user["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["amount_uzd"] == 5000
    assert body["amount_wei"] == str(5000 * 10**18)
    assert body["tx_hash"] is None


@pytest.mark.asyncio
async def test_create_withdrawal_requires_wallet(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _make_user(db_session, wallet=None, tg=62_000, oid="nowd")
    headers = {"Authorization": f"Bearer {_make_token(user.id)}"}
    response = await client.post(
        "/api/v1/withdrawals", json={"amount_uzd": 100}, headers=headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_own_withdrawals(
    client: AsyncClient, wallet_user: dict[str, Any]
) -> None:
    for amount in (100, 200):
        await client.post(
            "/api/v1/withdrawals",
            json={"amount_uzd": amount},
            headers=wallet_user["headers"],
        )
    response = await client.get("/api/v1/withdrawals", headers=wallet_user["headers"])
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_confirm_burns_and_marks_confirmed(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, wallet=WALLET, tg=63_000, oid="confuser")
    await _seed_deposit(db_session, user.id, 1_000_000)
    withdrawal = await withdrawals_service.create_withdrawal(db_session, user, 5000)
    await db_session.commit()

    with patch(
        "src.bank.service.send_via", new=AsyncMock(return_value=FAKE_TX)
    ) as mock_send:
        result = await bank_service.confirm_withdrawal(db_session, withdrawal.id)

    assert result.status == WithdrawalStatus.CONFIRMED.value
    assert result.tx_hash == FAKE_TX
    assert result.confirmed_at is not None
    role, contract, calldata = mock_send.call_args.args
    assert role is Role.BANK_OPS
    assert contract == settings.uzd_contract_address
    assert calldata.startswith(ADMIN_BURN_SELECTOR)  # adminBurn(address,uint256)


@pytest.mark.asyncio
async def test_reject_releases_without_onchain(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, wallet=WALLET, tg=64_000, oid="rejuser")
    await _seed_deposit(db_session, user.id, 1_000_000)
    withdrawal = await withdrawals_service.create_withdrawal(db_session, user, 5000)
    await db_session.commit()

    with patch(
        "src.bank.service.send_via", new=AsyncMock(return_value=FAKE_TX)
    ) as mock_send:
        result = await bank_service.reject_withdrawal(db_session, withdrawal.id)

    assert result.status == WithdrawalStatus.REJECTED.value
    assert result.tx_hash is None
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_no_double_burn(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, wallet=WALLET, tg=65_000, oid="dblburn")
    await _seed_deposit(db_session, user.id, 1_000_000)
    withdrawal = await withdrawals_service.create_withdrawal(db_session, user, 5000)
    await db_session.commit()

    with patch(
        "src.bank.service.send_via", new=AsyncMock(return_value=FAKE_TX)
    ) as mock_send:
        await bank_service.confirm_withdrawal(db_session, withdrawal.id)
        with pytest.raises(ConflictException):
            await bank_service.confirm_withdrawal(db_session, withdrawal.id)

    assert mock_send.call_count == 1  # burned exactly once


# --------------------------------------------------------------------------- #
# SECURITY — deposit-backed solvency cap (blocking review finding)              #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_withdrawal_over_deposit_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A user cannot file a withdrawal larger than their net bank deposits."""
    user = await _make_user(db_session, wallet=WALLET, tg=66_000, oid="capuser")
    await _seed_deposit(db_session, user.id, 100)  # only 100 UZD deposited
    headers = {"Authorization": f"Bearer {_make_token(user.id)}"}

    over = await client.post(
        "/api/v1/withdrawals", json={"amount_uzd": 500}, headers=headers
    )
    assert over.status_code == 400  # exceeds deposit-backed balance

    ok = await client.post(
        "/api/v1/withdrawals", json={"amount_uzd": 100}, headers=headers
    )
    assert ok.status_code == 200

    # Second withdrawal of 100 would take the total to 200 > 100 deposited.
    second = await client.post(
        "/api/v1/withdrawals", json={"amount_uzd": 100}, headers=headers
    )
    assert second.status_code == 400  # outstanding + new exceeds the cap


@pytest.mark.asyncio
async def test_confirm_refuses_burn_beyond_deposits(db_session: AsyncSession) -> None:
    """The exploit guard: confirming a withdrawal for a user with NO deposits
    must NOT burn (an attacker who bound a third party's wallet has no deposits),
    and must leave the row PENDING rather than stuck CONFIRMED-without-burn.

    The row is inserted directly to bypass the create-time cap and prove the
    authoritative confirm-time backstop independently.
    """
    user = await _make_user(db_session, wallet=WALLET, tg=67_000, oid="thief")
    withdrawal = Withdrawal(
        id=uuid.uuid4(),
        user_id=user.id,
        amount_uzd=5000,
        amount_wei=str(5000 * 10**18),
        status=WithdrawalStatus.PENDING.value,
    )
    db_session.add(withdrawal)
    await db_session.commit()
    withdrawal_id = withdrawal.id  # capture before the internal rollback expires it

    with (
        patch(
            "src.bank.service.send_via", new=AsyncMock(return_value=FAKE_TX)
        ) as mock_send,
        pytest.raises(BadRequestException),
    ):
        await bank_service.confirm_withdrawal(db_session, withdrawal_id)

    mock_send.assert_not_called()  # no on-chain burn of un-deposited funds
    refreshed = await withdrawals_service.get_withdrawal(db_session, withdrawal_id)
    assert refreshed is not None
    assert refreshed.status == WithdrawalStatus.PENDING.value  # rolled back
    assert refreshed.tx_hash is None


@pytest.mark.asyncio
async def test_confirm_burn_failure_rolls_back(db_session: AsyncSession) -> None:
    """A failed on-chain burn leaves the withdrawal PENDING and retriable
    (rollback-on-broadcast-failure), never CONFIRMED-without-burn."""
    user = await _make_user(db_session, wallet=WALLET, tg=68_000, oid="burnfail")
    await _seed_deposit(db_session, user.id, 1_000_000)
    withdrawal = await withdrawals_service.create_withdrawal(db_session, user, 5000)
    await db_session.commit()
    withdrawal_id = withdrawal.id  # capture before the internal rollback expires it

    with (
        patch(
            "src.bank.service.send_via",
            new=AsyncMock(side_effect=SignerError("broadcast failed")),
        ) as mock_send,
        pytest.raises(SignerError),
    ):
        await bank_service.confirm_withdrawal(db_session, withdrawal_id)

    assert mock_send.call_count == 1
    refreshed = await withdrawals_service.get_withdrawal(db_session, withdrawal_id)
    assert refreshed is not None
    assert refreshed.status == WithdrawalStatus.PENDING.value
    assert refreshed.tx_hash is None
