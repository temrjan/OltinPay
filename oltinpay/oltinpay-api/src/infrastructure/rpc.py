"""Minimal JSON-RPC client for zkSync Era Sepolia.

Uses the httpx dependency already present in the project. Avoids pulling
in web3.py: we only need read-only `eth_call` for contract views, and
that's a thin wrapper around a single HTTP POST.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from src.config import settings

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


class RpcError(Exception):
    """Non-HTTP JSON-RPC error returned by the node."""


def is_valid_address(address: str) -> bool:
    """True if `address` is a 40-hex-character EVM address with 0x prefix."""
    return bool(ADDRESS_RE.match(address))


def pad_address(address: str) -> str:
    """Left-pad a 0x-prefixed address to 32 bytes of hex (for eth_call data)."""
    if not is_valid_address(address):
        raise ValueError(f"Invalid EVM address: {address}")
    return address[2:].lower().rjust(64, "0")


async def eth_call(to: str, data: str, *, client: httpx.AsyncClient | None = None) -> str:
    """Execute an `eth_call` against `to` with hex-encoded `data`.

    Returns the raw hex string from the JSON-RPC response.
    Raises RpcError on node-reported errors.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
    }
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)
    try:
        response = await client.post(settings.zksync_rpc_url, json=payload)
        response.raise_for_status()
        body: dict[str, Any] = response.json()
    finally:
        if owns_client:
            await client.aclose()

    if "error" in body:
        raise RpcError(f"RPC error: {body['error']}")
    result = body.get("result")
    if not isinstance(result, str):
        raise RpcError(f"Unexpected RPC response: {body!r}")
    return result


def decode_uint256(hex_result: str) -> int:
    """Decode a 32-byte hex result from eth_call as a uint256."""
    if not hex_result or hex_result == "0x":
        return 0
    return int(hex_result, 16)
