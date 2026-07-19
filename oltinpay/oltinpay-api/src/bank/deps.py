"""HMAC authentication for the bank connector (/api/v1/bank/*).

Signature scheme (pinned — bank clients MUST match byte-for-byte):

    X-Bank-Signature = hex( HMAC-SHA256(BANK_HMAC_SECRET, body || ts || nonce) )

where ``body`` is the raw request body bytes, ``ts`` is the ``X-Bank-Timestamp``
header (unix seconds, UTF-8) and ``nonce`` is the ``X-Bank-Nonce`` header
(UTF-8), concatenated in that exact order. The digest is compared in constant
time.

Replay protection:
  * stale timestamp — rejected when |now - ts| > ``bank_hmac_max_skew_sec``.
  * replayed nonce — rejected via an in-memory TTL store.

HTTPS is assumed at the edge; production adds mTLS.

Accepted limitation (spec §8): the nonce store is in-process, consistent with
the single-writer deploy invariant. It does NOT survive a restart, so a replay
within the timestamp window immediately after a restart is theoretically
possible. SEAM: swap ``_replay_guard`` for a Redis/DB-backed store
(``redis_client.py`` exists but is unused at runtime) for a multi-process or
restart-durable deployment.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import HTTPException, Request, status

from src.common.exceptions import UnauthorizedException
from src.config import settings


def compute_signature(secret: str, body: bytes, timestamp: str, nonce: str) -> str:
    """Return the hex HMAC-SHA256 over ``body || timestamp || nonce``."""
    message = body + timestamp.encode("utf-8") + nonce.encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


class _NonceReplayGuard:
    """In-memory nonce store with TTL eviction (single-process)."""

    def __init__(self, ttl_sec: int) -> None:
        self._ttl = ttl_sec
        self._seen: dict[str, float] = {}

    def check_and_store(self, nonce: str, now: float) -> bool:
        """Return True if ``nonce`` is fresh (and record it); False if replayed."""
        # Evict expired entries so the store cannot grow without bound.
        expired = [n for n, exp in self._seen.items() if exp <= now]
        for n in expired:
            del self._seen[n]
        if nonce in self._seen:
            return False
        self._seen[nonce] = now + self._ttl
        return True


# TTL covers the whole window in which a captured request could still be
# replayed with an in-window timestamp (both past and future skew).
_replay_guard = _NonceReplayGuard(ttl_sec=2 * settings.bank_hmac_max_skew_sec)


async def require_bank_auth(request: Request) -> None:
    """FastAPI dependency guarding every /api/v1/bank/* route."""
    secret = settings.bank_hmac_secret
    if secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bank authentication is not configured on the server.",
        )

    signature = request.headers.get("X-Bank-Signature")
    timestamp = request.headers.get("X-Bank-Timestamp")
    nonce = request.headers.get("X-Bank-Nonce")
    if not signature or not timestamp or not nonce:
        raise UnauthorizedException("Missing bank authentication headers")

    try:
        ts_value = int(timestamp)
    except ValueError as exc:
        raise UnauthorizedException("Invalid X-Bank-Timestamp") from exc

    now = time.time()
    if abs(now - ts_value) > settings.bank_hmac_max_skew_sec:
        raise UnauthorizedException("Stale X-Bank-Timestamp")

    body = await request.body()
    expected = compute_signature(secret.get_secret_value(), body, timestamp, nonce)
    if not hmac.compare_digest(expected, signature):
        raise UnauthorizedException("Invalid bank signature")

    # Signature is valid — now (and only now) burn the nonce to block replays.
    if not _replay_guard.check_and_store(nonce, now):
        raise UnauthorizedException("Replayed X-Bank-Nonce")
