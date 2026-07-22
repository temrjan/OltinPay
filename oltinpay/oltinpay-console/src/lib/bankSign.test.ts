import { describe, expect, it } from "vitest";

import { computeSignature } from "./bankSign";

// Golden vector generated from the API's bank/deps.compute_signature
// (HMAC-SHA256(secret, body||ts||nonce), hex). If the first test fails, the
// Console's signing has drifted from the pinned bank auth scheme and the API
// would 401 every bank call — the single highest integration risk (spec §Тест).
const SECRET = "console-test-secret";
const BODY = '{"grams":1000,"auditRef":"AUD-1"}';
const TS = "1700000000";
const NONCE = "11111111-1111-1111-1111-111111111111";
const GOLDEN = "41840a5b24954498662813f6590a1f4bd18743ca1f0aa99b45621b6cb88579ce";

describe("computeSignature", () => {
  it("matches the API compute_signature byte-for-byte", () => {
    const sig = computeSignature(SECRET, Buffer.from(BODY, "utf-8"), TS, NONCE);
    expect(sig).toBe(GOLDEN);
  });

  it("changes if a single body byte changes (byte-sensitive)", () => {
    // Proves the test is not tautological: any drift in the forwarded bytes
    // (here a trailing space) produces a different signature.
    const sig = computeSignature(
      SECRET,
      Buffer.from(BODY + " ", "utf-8"),
      TS,
      NONCE,
    );
    expect(sig).not.toBe(GOLDEN);
  });

  it("changes if the nonce changes", () => {
    const sig = computeSignature(SECRET, Buffer.from(BODY, "utf-8"), TS, "other");
    expect(sig).not.toBe(GOLDEN);
  });
});
