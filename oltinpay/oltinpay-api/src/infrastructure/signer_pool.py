"""Serialized, per-key transaction signer for zkSync Era Sepolia.

Refactor of the former ``admin_tx.py``. The old code signed every mint with a
single admin key and read ``eth_getTransactionCount(addr, "pending")`` *per
call* — two concurrent requests would read the same pending nonce and collide
(BLOCKER A1). This module replaces that with a signer that serializes sends per
key and tracks the nonce in a local counter.

Design (spec §3 — Design-A):
  * One EOA per role — ``KEY_BANK_OPS`` (UZD mint/burn), ``KEY_RESERVE``
    (ReserveAttestor.postAnswer), ``KEY_UZS`` (UzsUsdFeed.postAnswer) and
    ``KEY_XAU`` (external keeper only — the API never signs XAU).
  * Each signer serializes its sends behind an ``asyncio.Lock`` and keeps the
    nonce in a **local counter**: initialised from
    ``eth_getTransactionCount(addr, "latest")`` on first use, incremented after
    every successful ``eth_sendRawTransaction`` and re-synced from "latest" when
    the node reports "nonce too low" (a stale counter after a restart or an
    out-of-band transaction). Exactly ONE in-flight transaction per key by
    construction, so nonces can never race.

Deploy invariant (A1, ratified): exactly ONE writing process per key. The API
runs single-worker and ``keeper-uzs`` is retired, so ``/fx`` is the sole
KEY_UZS writer. This local nonce is correct *only* under that invariant.

SEAM for a future distributed deployment: ``SignerPool`` builds signers through
an injectable ``signer_factory``. Swap in a Redis-backed signer (atomic INCR +
a short lease) that satisfies the ``Signer`` protocol to run more than one
writer per key. Redis is deliberately NOT implemented here (rules #5 — no infra
under hypothesis; the INCR↔broadcast crash-window needs its own design). The
production path is recorded in the honesty box.

eth-account is the only dependency — no full web3.py. zkSync Era accepts plain
EIP-1559 transactions from EOAs.
"""

from __future__ import annotations

import asyncio
import logging
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

import httpx
from eth_account import Account

from src.config import settings
from src.infrastructure.rpc import is_valid_address, pad_address

if TYPE_CHECKING:
    from collections.abc import Callable

    from eth_account.signers.local import LocalAccount
    from pydantic import SecretStr

logger = logging.getLogger(__name__)

# Function selectors (first 4 bytes of keccak256 of the signature).
MINT_SELECTOR = "0x40c10f19"  # mint(address,uint256)
ADMIN_BURN_SELECTOR = "0x06dd0419"  # adminBurn(address,uint256)  (BURNER_ROLE)
POST_ANSWER_SELECTOR = "0xd7fc7b18"  # postAnswer(int256)

# Receipt polling (BLOCKER B2): a mempool-accepted tx can still revert on-chain.
RECEIPT_TIMEOUT_SEC = 60.0  # zkSync Sepolia mines in seconds; generous ceiling
RECEIPT_POLL_SEC = 2.0


class Role(StrEnum):
    """A writing role, each mapped to its own private key in settings."""

    BANK_OPS = "bank_ops"  # UZD.mint / UZD.adminBurn
    RESERVE = "reserve"  # ReserveAttestor.postAnswer
    UZS = "uzs"  # UzsUsdFeed.postAnswer
    XAU = "xau"  # external keeper-xau only (never signed by the API)


_ROLE_KEY_ATTR: dict[Role, str] = {
    Role.BANK_OPS: "key_bank_ops",
    Role.RESERVE: "key_reserve",
    Role.UZS: "key_uzs",
    Role.XAU: "key_xau",
}


class SignerUnconfigured(RuntimeError):
    """Raised when the private key for a role is not configured."""


class SignerError(RuntimeError):
    """Raised when a signed transaction could not be built or broadcast."""


class _NonceTooLow(RuntimeError):
    """Internal: the node rejected the tx because the local nonce is stale."""


# --------------------------------------------------------------------------- #
# calldata encoders                                                           #
# --------------------------------------------------------------------------- #
def _encode_uint256(value: int) -> str:
    if value < 0 or value >= 2**256:
        raise ValueError(f"Value out of uint256 range: {value}")
    return f"{value:064x}"


def _encode_int256(value: int) -> str:
    """Two's-complement encode a signed int256 into a 32-byte hex word."""
    if value < -(2**255) or value >= 2**255:
        raise ValueError(f"Value out of int256 range: {value}")
    return f"{value & (2**256 - 1):064x}"


def encode_mint_calldata(to: str, amount_wei: int) -> str:
    """UZD.mint(address,uint256) calldata."""
    if not is_valid_address(to):
        raise ValueError(f"Invalid recipient address: {to}")
    return "0x" + MINT_SELECTOR[2:] + pad_address(to) + _encode_uint256(amount_wei)


def encode_admin_burn_calldata(holder: str, amount_wei: int) -> str:
    """UZD.adminBurn(address,uint256) calldata (BURNER_ROLE)."""
    if not is_valid_address(holder):
        raise ValueError(f"Invalid holder address: {holder}")
    return (
        "0x" + ADMIN_BURN_SELECTOR[2:] + pad_address(holder) + _encode_uint256(amount_wei)
    )


def encode_post_answer_calldata(answer: int) -> str:
    """Attestor.postAnswer(int256) calldata (signed answer)."""
    return "0x" + POST_ANSWER_SELECTOR[2:] + _encode_int256(answer)


# --------------------------------------------------------------------------- #
# signer                                                                       #
# --------------------------------------------------------------------------- #
class Signer(Protocol):
    """The swap interface for the SignerPool seam (local today, Redis later)."""

    address: str

    async def send(self, contract: str, data: str) -> str:
        """Sign and broadcast a transaction, returning its hash."""
        ...


async def _rpc(method: str, params: list[object], client: httpx.AsyncClient) -> object:
    response = await client.post(
        settings.zksync_rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise SignerError(f"{method}: {body['error']}")
    return body.get("result")


class NonceManagedSigner:
    """A single EOA whose sends are serialized with a local nonce counter.

    One in-flight transaction at a time (per-key ``asyncio.Lock``). The nonce is
    lazily initialised from "latest", advanced on success, and re-synced once on
    a "nonce too low" error.
    """

    def __init__(self, account: LocalAccount) -> None:
        self._account = account
        self.address: str = account.address
        self._lock = asyncio.Lock()
        self._nonce: int | None = None

    async def send(self, contract: str, data: str) -> str:
        async with self._lock, httpx.AsyncClient(timeout=15.0) as client:
            if self._nonce is None:
                self._nonce = await self._fetch_latest_nonce(client)
            try:
                return await self._build_sign_send(contract, data, client)
            except _NonceTooLow:
                # Local counter drifted (restart / external tx). Re-sync from
                # the chain and retry exactly once.
                self._nonce = await self._fetch_latest_nonce(client)
                logger.warning(
                    "signer_nonce_resync address=%s nonce=%s", self.address, self._nonce
                )
                return await self._build_sign_send(contract, data, client)

    async def _fetch_latest_nonce(self, client: httpx.AsyncClient) -> int:
        raw = await _rpc("eth_getTransactionCount", [self.address, "latest"], client)
        if not isinstance(raw, str):
            raise SignerError("Unexpected RPC response for nonce")
        return int(raw, 16)

    async def _build_sign_send(
        self, contract: str, data: str, client: httpx.AsyncClient
    ) -> str:
        assert self._nonce is not None  # invariant guaranteed by send()
        nonce = self._nonce

        # Three independent reads — gather to shrink how long the per-key lock is
        # held (P1). maxPriorityFeePerGas may be unsupported -> tolerated below.
        gas_price_hex, est_hex, priority_hex = await asyncio.gather(
            _rpc("eth_gasPrice", [], client),
            _rpc(
                "eth_estimateGas",
                [{"from": self.address, "to": contract, "data": data}],
                client,
            ),
            _rpc("eth_maxPriorityFeePerGas", [], client),
        )
        if not isinstance(gas_price_hex, str):
            raise SignerError("Unexpected RPC response for gasPrice")
        if not isinstance(est_hex, str):
            raise SignerError("Unexpected RPC response for estimateGas")
        base_fee = int(gas_price_hex, 16)
        # 20% headroom — EraVM estimation is usually tight but can spike.
        gas_limit = int(est_hex, 16) * 12 // 10
        max_priority = int(priority_hex, 16) if isinstance(priority_hex, str) else 0
        # Standard formula: inclusion even if base_fee doubles.
        max_fee = base_fee * 2 + max_priority

        tx = {
            "chainId": settings.zksync_chain_id,
            "nonce": nonce,
            "to": contract,
            "value": 0,
            "data": data,
            "gas": gas_limit,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority,
            "type": 2,
        }
        signed = self._account.sign_transaction(tx)  # type: ignore[arg-type]
        raw_hex = "0x" + signed.raw_transaction.hex()

        tx_hash = await self._send_raw(raw_hex, client)
        # A mempool-accepted tx consumes the nonce even if it later reverts, so
        # advance the counter now. Then require a successful mined receipt
        # (BLOCKER B2) — a reverted mint/burn must NOT be reported as success.
        self._nonce = nonce + 1
        await self._wait_for_receipt(tx_hash, client)
        logger.info(
            "signer_tx_sent address=%s to=%s nonce=%s tx=%s",
            self.address,
            contract,
            nonce,
            tx_hash,
        )
        return tx_hash

    async def _send_raw(self, raw_hex: str, client: httpx.AsyncClient) -> str:
        response = await client.post(
            settings.zksync_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_sendRawTransaction",
                "params": [raw_hex],
            },
        )
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            message = str(body["error"]).lower()
            if "nonce too low" in message or "nonce is too low" in message:
                raise _NonceTooLow(str(body["error"]))
            raise SignerError(f"eth_sendRawTransaction: {body['error']}")
        result = body.get("result")
        if not isinstance(result, str):
            raise SignerError(f"Unexpected sendRawTransaction result: {result!r}")
        return result

    async def _wait_for_receipt(
        self, tx_hash: str, client: httpx.AsyncClient
    ) -> dict[str, object]:
        """Poll until the tx is mined and require ``status == 1`` (BLOCKER B2).

        ``eth_sendRawTransaction`` only confirms mempool acceptance; a mint/burn
        can still revert on-chain (e.g. ``adminBurn`` on an insufficient
        balance). Without this, a reverted tx would be reported as success and
        the DB (a CONFIRMED withdrawal / a deposit row) would permanently diverge
        from chain. Raises :class:`SignerError` on revert or if no receipt
        appears within :data:`RECEIPT_TIMEOUT_SEC`.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + RECEIPT_TIMEOUT_SEC
        while True:
            receipt = await _rpc("eth_getTransactionReceipt", [tx_hash], client)
            if isinstance(receipt, dict):
                status = receipt.get("status")
                if isinstance(status, str) and int(status, 16) == 1:
                    return receipt
                raise SignerError(
                    f"transaction reverted (status={status!r}): {tx_hash}"
                )
            if loop.time() >= deadline:
                raise SignerError(f"receipt not mined within timeout: {tx_hash}")
            await asyncio.sleep(RECEIPT_POLL_SEC)


# --------------------------------------------------------------------------- #
# pool                                                                         #
# --------------------------------------------------------------------------- #
class SignerPool:
    """Caches one :class:`Signer` per EOA address, resolved from a role key."""

    def __init__(
        self, signer_factory: Callable[[LocalAccount], Signer] = NonceManagedSigner
    ) -> None:
        # SEAM: pass a Redis-backed factory here for multi-writer deployments.
        self._signer_factory = signer_factory
        self._signers: dict[str, Signer] = {}

    def for_key(self, role: Role) -> Signer:
        secret: SecretStr | None = getattr(settings, _ROLE_KEY_ATTR[role])
        if secret is None:
            raise SignerUnconfigured(
                f"{_ROLE_KEY_ATTR[role].upper()} is not configured on the server."
            )
        account: LocalAccount = Account.from_key(secret.get_secret_value())
        signer = self._signers.get(account.address)
        if signer is None:
            signer = self._signer_factory(account)
            self._signers[account.address] = signer
        return signer


# Module-level shared pool — the single writer per key lives here.
pool = SignerPool()


async def send_via(role: Role, contract: str, data: str) -> str:
    """Sign+broadcast ``data`` to ``contract`` using ``role``'s serialized signer.

    Service modules import this and patch it at their own usage site in tests
    (``patch("src.<module>.service.send_via", AsyncMock(...))``).
    """
    return await pool.for_key(role).send(contract, data)


__all__ = [
    "Role",
    "Signer",
    "SignerError",
    "SignerUnconfigured",
    "encode_admin_burn_calldata",
    "encode_mint_calldata",
    "encode_post_answer_calldata",
    "pool",
    "send_via",
]
