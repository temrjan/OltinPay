import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { bankForward } from "./bankForward";
import { computeSignature } from "./bankSign";

describe("bankForward", () => {
  beforeEach(() => {
    process.env.BANK_HMAC_SECRET = "console-test-secret";
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.BANK_HMAC_SECRET;
  });

  it("signs the EXACT bytes it forwards (invariant #2: sign == forward)", async () => {
    let captured: RequestInit | undefined;
    const fetchMock = vi.fn((_url: string, init: RequestInit) => {
      captured = init;
      return Promise.resolve(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const payload = { grams: 1000, auditRef: "AUD-1" };
    const result = await bankForward("/bank/attestations", "POST", payload);
    expect(result.status).toBe(200);

    expect(captured).toBeDefined();
    const headers = captured!.headers as Record<string, string>;
    const sentBytes = Buffer.from(captured!.body as Uint8Array);

    // The signature the API receives must be HMAC over the exact forwarded bytes
    // — recomputing over the captured body+ts+nonce must reproduce it. If the
    // body were re-serialized after signing, this would diverge.
    const expected = computeSignature(
      "console-test-secret",
      sentBytes,
      headers["X-Bank-Timestamp"],
      headers["X-Bank-Nonce"],
    );
    expect(headers["X-Bank-Signature"]).toBe(expected);
    // Serialized exactly once — the forwarded body is the payload JSON.
    expect(sentBytes.toString("utf-8")).toBe(JSON.stringify(payload));
  });

  it("returns 503 without calling the API when the secret is unset", async () => {
    delete process.env.BANK_HMAC_SECRET;
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const result = await bankForward("/bank/fx", "POST", { uzsPerUsd: 12500 });
    expect(result.status).toBe(503);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
