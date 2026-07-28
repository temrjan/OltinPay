#!/usr/bin/env python3
"""OltinPay feed keeper — keeps the XAU / UZS / RESERVE attestor feeds fresh.

Each run re-posts every feed's *last on-chain answer* via
``Attestor.postAnswer(int256)``. The Attestor self-stamps
``updatedAt = block.timestamp`` on every post, so a re-post of the identical
value is a valid heartbeat that resets staleness. That is all the on-chain
consumers gate on: ``Exchange.buy/sell`` (XAU + UZS) and OLTIN PoR-mint
(RESERVE) revert once a feed is older than its ``maxAge``.

The posted VALUE is deliberately frozen (last answer re-posted). Real market
prices are synced separately by the ``npm run keeper:all`` ops command (run the
morning of a demo). This keeper only guarantees freshness — the thing that was
silently killing the exchange.

Standalone by design (ratified Gate-1): eth_account + stdlib JSON-RPC only, no
project imports, no contracts repo on prod. The signing key is read from a file
and holds POSTER_ROLE on all three attestors — never the deployer key.

Usage:
    keeper.py            # post each stale feed, log + exit 1 on any failure
    keeper.py --dry-run  # read + decide + print calldata, send nothing
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass

# eth_account is imported lazily inside run() so the pure helpers (and their
# unit tests) import without the signing dependency present.

# --- Config (env-overridable; addresses are deployment constants) -------------

RPC_URL = os.environ.get("KEEPER_RPC_URL", "https://sepolia.era.zksync.dev")
CHAIN_ID = int(os.environ.get("KEEPER_CHAIN_ID", "300"))
KEY_FILE = os.environ.get("KEEPER_KEY_FILE", "/root/oltinpay-keeper/poster.key")
LOG_FILE = os.environ.get("KEEPER_LOG_FILE", "/root/oltinpay-keeper/keeper.log")
# POSTER_ROLE holder on all three attestors (docs/DEPLOYMENTS.md). The key in
# KEY_FILE must resolve to this address, otherwise postAnswer reverts on-chain.
EXPECTED_POSTER = "0xfaFB46cC23705058EE9E1a96f64B0f273B87405e"

POST_ANSWER_SELECTOR = "0xd7fc7b18"        # postAnswer(int256)
LATEST_ROUND_DATA_SELECTOR = "0xfeaf968c"  # latestRoundData()

RECEIPT_TIMEOUT_SEC = 90.0
RECEIPT_POLL_SEC = 2.0
RPC_TIMEOUT_SEC = 30.0


@dataclass(frozen=True)
class Feed:
    label: str
    address: str
    max_age: int      # on-chain staleness limit (seconds)
    heartbeat: int    # re-post once the feed is older than this (< max_age)


# heartbeat chosen so that (heartbeat + timer_period) stays well under max_age.
# One 30-min systemd timer drives all three: XAU/RESERVE re-post almost every
# run (heartbeat 25 min < 30 min), UZS re-posts ~daily (heartbeat 18 h).
FEEDS = (
    Feed("XAU", "0xe0AFc7eD0c6028b8172C2b108624168d235e8BFD", max_age=3600, heartbeat=1500),
    Feed("RESERVE", "0x9413F60295dcf7D81fcb69eE256029900B107d1B", max_age=3600, heartbeat=1500),
    Feed("UZS", "0x637347fd661cFFAE9B562aFA394A392214fa24aD", max_age=259200, heartbeat=64800),
)


class RpcError(RuntimeError):
    """A JSON-RPC node returned an error object."""


class PostError(RuntimeError):
    """A post transaction failed (reverted, timed out, or was rejected)."""


# --- Pure helpers (unit-tested) -----------------------------------------------

def encode_int256(value: int) -> str:
    """Two's-complement 32-byte hex (no 0x), matching signer_pool._encode_int256."""
    if value < -(2 ** 255) or value >= 2 ** 255:
        raise ValueError(f"int256 out of range: {value}")
    return "%064x" % (value & (2 ** 256 - 1))


def decode_int256(word_hex: str) -> int:
    """Decode a 32-byte ABI word (hex, no 0x) as a signed int256."""
    value = int(word_hex, 16)
    if value >= 2 ** 255:
        value -= 2 ** 256
    return value


def encode_post_answer(answer: int) -> str:
    """Calldata (with 0x) for postAnswer(int256)."""
    return POST_ANSWER_SELECTOR + encode_int256(answer)


def decide(age: int, heartbeat: int) -> str:
    """POST once the feed is at/over its heartbeat, else SKIP (still fresh)."""
    return "POST" if age >= heartbeat else "SKIP"


# --- JSON-RPC (stdlib only) ---------------------------------------------------

def rpc(method: str, params: list) -> object:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    req = urllib.request.Request(
        RPC_URL, data=payload.encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=RPC_TIMEOUT_SEC) as resp:
        body = json.loads(resp.read())
    if body.get("error"):
        raise RpcError(f"{method}: {body['error']}")
    return body["result"]


def chain_now() -> int:
    """L2 block timestamp — never the local clock (matches the TS keepers)."""
    block = rpc("eth_getBlockByNumber", ["latest", False])
    return int(block["timestamp"], 16)


def read_feed(address: str) -> tuple[int, int]:
    """Return (answer, updatedAt) from latestRoundData()."""
    result = rpc("eth_call", [{"to": address, "data": LATEST_ROUND_DATA_SELECTOR}, "latest"])
    data = result[2:]  # strip 0x; 5 ABI words
    answer = decode_int256(data[64:128])
    updated_at = int(data[192:256], 16)
    return answer, updated_at


def wait_receipt(tx_hash: str) -> dict:
    deadline = time.monotonic() + RECEIPT_TIMEOUT_SEC
    while True:
        receipt = rpc("eth_getTransactionReceipt", [tx_hash])
        if receipt is not None:
            return receipt
        if time.monotonic() >= deadline:
            raise PostError(f"receipt timeout for {tx_hash}")
        time.sleep(RECEIPT_POLL_SEC)


def post_answer(account, feed_address: str, answer: int) -> str:
    """Sign + send an EIP-1559 postAnswer tx (signer_pool.py pattern)."""
    data = encode_post_answer(answer)
    sender = account.address
    nonce = int(rpc("eth_getTransactionCount", [sender, "pending"]), 16)
    base_fee = int(rpc("eth_gasPrice", []), 16)
    try:
        max_priority = int(rpc("eth_maxPriorityFeePerGas", []), 16)
    except RpcError:
        max_priority = 0
    est = int(
        rpc("eth_estimateGas", [{"from": sender, "to": feed_address, "data": data, "value": "0x0"}]),
        16,
    )
    tx = {
        "chainId": CHAIN_ID,
        "nonce": nonce,
        "to": feed_address,
        "value": 0,
        "data": data,
        "gas": est * 12 // 10,               # 20% headroom
        "maxFeePerGas": base_fee * 2 + max_priority,
        "maxPriorityFeePerGas": max_priority,
        "type": 2,
    }
    signed = account.sign_transaction(tx)
    tx_hash = rpc("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])
    receipt = wait_receipt(tx_hash)
    if int(receipt["status"], 16) != 1:
        raise PostError(f"tx reverted: {tx_hash}")
    return tx_hash


# --- Logging ------------------------------------------------------------------

def log(line: str) -> None:
    """Append to the keeper log and echo to stdout (journald picks it up)."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
    entry = f"{stamp} {line}"
    print(entry, flush=True)
    try:
        with open(LOG_FILE, "a") as fh:
            fh.write(entry + "\n")
    except OSError as exc:  # log-file failure must not abort the run
        print(f"{stamp} WARN log-file write failed: {exc}", flush=True)


# --- Run ----------------------------------------------------------------------

def run(dry_run: bool = False) -> int:
    from eth_account import Account  # lazy: keeps pure helpers import-safe

    with open(KEY_FILE) as fh:
        account = Account.from_key(fh.read().strip())
    if account.address.lower() != EXPECTED_POSTER.lower():
        log(f"WARN poster address {account.address} != expected {EXPECTED_POSTER} "
            f"(posts will revert if it lacks POSTER_ROLE)")

    now = chain_now()
    failures = 0
    for feed in FEEDS:
        try:
            answer, updated_at = read_feed(feed.address)
        except (RpcError, OSError, ValueError) as exc:
            failures += 1
            log(f"POST_FAIL({feed.label}) read latestRoundData: {exc}")
            continue

        age = now - updated_at
        if answer <= 0:
            # Never re-post a non-positive answer — consumers reject it and it
            # would be a garbage heartbeat. Should not happen for our 3 feeds.
            log(f"POST_FAIL({feed.label}) non-positive last answer={answer}, "
                f"nothing valid to refresh")
            failures += 1
            continue

        if decide(age, feed.heartbeat) == "SKIP":
            log(f"SKIP({feed.label}) fresh: age={age}s < heartbeat={feed.heartbeat}s")
            continue

        if dry_run:
            log(f"DRY({feed.label}) age={age}s -> would postAnswer({answer}) "
                f"calldata={encode_post_answer(answer)}")
            continue

        try:
            tx_hash = post_answer(account, feed.address, answer)
            log(f"POST_OK({feed.label}) answer={answer} age_before={age}s tx={tx_hash}")
        except (RpcError, PostError, OSError) as exc:
            failures += 1
            log(f"POST_FAIL({feed.label}) age={age}s: {exc}")

    return 1 if failures else 0


def main() -> int:
    dry_run = "--dry-run" in sys.argv[1:]
    try:
        return run(dry_run=dry_run)
    except Exception as exc:  # never die silently — the stale exchange did
        log(f"POST_FAIL(keeper) fatal: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
