import { randomUUID } from "node:crypto";

import { computeSignature } from "./bankSign";

// Server-only. Signs a bank request with BANK_HMAC_SECRET and forwards it to the
// API (E2 — the secret never reaches the browser). Enforces invariant #2
// (sign-then-forward the SAME bytes): the JSON payload is serialized ONCE into a
// Buffer; that exact Buffer is both signed and sent as the body. Never
// re-serialize between signing and forwarding.

const API_URL = process.env.API_URL ?? "http://localhost:8000/api/v1";

export interface BankResult {
  status: number;
  body: unknown;
}

export async function bankForward(
  path: string,
  method: "GET" | "POST",
  payload?: unknown,
): Promise<BankResult> {
  const secret = process.env.BANK_HMAC_SECRET;
  if (!secret) {
    return {
      status: 503,
      body: { error: "BANK_HMAC_SECRET is not configured on the server." },
    };
  }

  // Serialize once — sign and forward these exact bytes.
  const bodyBuf =
    payload === undefined
      ? Buffer.alloc(0)
      : Buffer.from(JSON.stringify(payload), "utf-8");
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const nonce = randomUUID();
  const signature = computeSignature(secret, bodyBuf, timestamp, nonce);

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Bank-Signature": signature,
      "X-Bank-Timestamp": timestamp,
      "X-Bank-Nonce": nonce,
    },
    body: method === "POST" ? bodyBuf : undefined,
    cache: "no-store",
  });
  const body: unknown = await res.json().catch(() => ({}));
  return { status: res.status, body };
}
