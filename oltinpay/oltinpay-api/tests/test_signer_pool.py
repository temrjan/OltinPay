"""Unit tests for the SignerPool nonce management (no HTTP client).

The RPC is mocked with respx. Concurrency is driven with asyncio.gather to prove
the per-key serialization: exactly one in-flight tx, monotonic nonces, and a
re-sync after a "nonce too low" reply.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import respx
import rlp
from eth_account import Account
from eth_utils import to_int

from src.config import settings
from src.infrastructure.signer_pool import (
    NonceManagedSigner,
    SignerError,
    encode_mint_calldata,
)

# Deterministic well-known test key (Hardhat account #1). Test-only.
TEST_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
CONTRACT = "0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32"
RECIPIENT = "0xA0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"


def _res(result: str) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})


def _nonce_of(raw_tx_hex: str) -> int:
    """Decode the nonce from a signed EIP-1559 (type-2) transaction."""
    payload = bytes.fromhex(raw_tx_hex[2:])
    assert payload[0] == 0x02  # EIP-1559 envelope
    fields = rlp.decode(payload[1:])
    return to_int(fields[1])  # [chainId, nonce, ...]


class _RpcStub:
    """Stateful JSON-RPC handler for respx."""

    def __init__(
        self,
        start_nonce: int,
        fail_first_send: bool = False,
        receipt_status: str = "0x1",
    ) -> None:
        self.chain_nonce = start_nonce
        self.fail_first_send = fail_first_send
        self.receipt_status = receipt_status
        self.calls: dict[str, int] = {}
        self.sent_nonces: list[int] = []
        self._send_count = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        method = json.loads(request.content)["method"]
        self.calls[method] = self.calls.get(method, 0) + 1

        if method == "eth_getTransactionCount":
            return _res(hex(self.chain_nonce))
        if method == "eth_gasPrice":
            return _res(hex(10**9))
        if method == "eth_estimateGas":
            return _res(hex(100_000))
        if method == "eth_maxPriorityFeePerGas":
            return _res(hex(10**8))
        if method == "eth_sendRawTransaction":
            raw = json.loads(request.content)["params"][0]
            self._send_count += 1
            if self.fail_first_send and self._send_count == 1:
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "error": {"code": -32000, "message": "nonce too low"},
                    },
                )
            self.sent_nonces.append(_nonce_of(raw))
            return _res("0x" + f"{self._send_count:064x}")
        if method == "eth_getTransactionReceipt":
            # B2: the signer polls for a mined receipt and requires status==1.
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"status": self.receipt_status},
                },
            )
        raise AssertionError(f"unexpected RPC method: {method}")


@pytest.mark.asyncio
async def test_concurrent_sends_serialize_with_monotonic_nonces() -> None:
    signer = NonceManagedSigner(Account.from_key(TEST_KEY))
    stub = _RpcStub(start_nonce=0)
    data = encode_mint_calldata(RECIPIENT, 10**18)

    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(side_effect=stub)
        results = await asyncio.gather(
            *(signer.send(CONTRACT, data) for _ in range(5))
        )

    # Five distinct broadcasts.
    assert len(results) == 5
    assert len(set(results)) == 5
    # Serialization: the nonce was fetched from chain exactly once; the other
    # four sends reused the local counter (a broken lock would fetch 5 times).
    assert stub.calls["eth_getTransactionCount"] == 1
    assert stub.calls["eth_sendRawTransaction"] == 5
    # Monotonic, gap-free nonces and an advanced local counter.
    assert stub.sent_nonces == [0, 1, 2, 3, 4]
    assert signer._nonce == 5


@pytest.mark.asyncio
async def test_resync_on_nonce_too_low() -> None:
    signer = NonceManagedSigner(Account.from_key(TEST_KEY))
    # Local counter will init to 5, the first send is rejected as "nonce too low",
    # then the signer re-fetches (chain now reports 6) and retries successfully.
    stub = _RpcStub(start_nonce=5, fail_first_send=True)
    data = encode_mint_calldata(RECIPIENT, 10**18)

    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(side_effect=stub)
        stub.chain_nonce = 5
        # Bump the chain nonce right before the retry read to exercise re-sync.
        original = stub.__call__

        def _handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            if (
                body["method"] == "eth_getTransactionCount"
                and stub.calls.get("eth_sendRawTransaction", 0) >= 1
            ):
                stub.chain_nonce = 6
            return original(request)

        mock.post("").mock(side_effect=_handler)
        tx_hash = await signer.send(CONTRACT, data)

    assert tx_hash.startswith("0x")
    assert stub.calls["eth_getTransactionCount"] == 2  # initial + re-sync
    assert stub.calls["eth_sendRawTransaction"] == 2  # failed + retried
    assert stub.sent_nonces == [6]  # retried with the re-synced nonce
    assert signer._nonce == 7


@pytest.mark.asyncio
async def test_send_raises_on_reverted_receipt() -> None:
    """BLOCKER B2: a mined-but-reverted tx (status 0x0) must raise, not succeed.

    ``eth_sendRawTransaction`` only confirms mempool acceptance; a reverted burn/
    mint would otherwise be reported as success and desync the DB from chain. The
    nonce still advances (a reverted tx consumes it on-chain), keeping the local
    counter in step.
    """
    signer = NonceManagedSigner(Account.from_key(TEST_KEY))
    stub = _RpcStub(start_nonce=3, receipt_status="0x0")
    data = encode_mint_calldata(RECIPIENT, 10**18)

    with respx.mock(base_url=settings.zksync_rpc_url) as mock:
        mock.post("").mock(side_effect=stub)
        with pytest.raises(SignerError, match="reverted"):
            await signer.send(CONTRACT, data)

    assert stub.calls["eth_sendRawTransaction"] == 1
    assert stub.calls["eth_getTransactionReceipt"] == 1
    assert signer._nonce == 4  # advanced past the reverted-but-mined tx
