import { createHmac } from "node:crypto";

/**
 * HMAC-SHA256(secret, body || timestamp || nonce) as lowercase hex.
 *
 * Mirrors the API's `bank/deps.compute_signature` byte-for-byte (the bank auth
 * scheme is pinned — a single differing byte makes the API reject every call
 * with 401). Server-only: `BANK_HMAC_SECRET` must never reach the browser (E2).
 *
 * INVARIANT (sign-then-forward the SAME bytes): `body` is the exact byte string
 * that will be forwarded to the API. Serialize the JSON payload ONCE into a
 * Buffer, sign that Buffer, and forward that identical Buffer — never
 * re-serialize between signing and forwarding (key order / whitespace / encoding
 * drift would break the signature).
 */
export function computeSignature(
  secret: string,
  body: Buffer,
  timestamp: string,
  nonce: string,
): string {
  const message = Buffer.concat([
    body,
    Buffer.from(timestamp, "utf-8"),
    Buffer.from(nonce, "utf-8"),
  ]);
  return createHmac("sha256", Buffer.from(secret, "utf-8"))
    .update(message)
    .digest("hex");
}
