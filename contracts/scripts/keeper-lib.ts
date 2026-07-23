/**
 * Shared keeper logic: post/skip/refuse decisions and input parsers, extracted
 * so they can be unit tested without RPC or a chain. Keepers are thin scripts
 * over this module.
 *
 * Exit code contract (used by cron alerting in P4-A):
 *   0 = posted, 2 = deliberate skip, 1 = refusal/error.
 *
 * Clock discipline (spec P1-A): `now` for on-chain age comes from the L2 block
 * timestamp, `now` for the Chainlink source age from the mainnet block
 * timestamp; the local clock is only used for the CBU calendar date, where
 * minutes of skew are irrelevant.
 */

export const EXIT_POSTED = 0;
export const EXIT_SKIPPED = 2;
export const EXIT_FAILED = 1;

export interface DecideInput {
  /** Current on-chain answer (0n = never posted). */
  current: bigint;
  /** On-chain updatedAt of the current answer, seconds. */
  currentUpdatedAt: bigint;
  /** New value from the source. */
  next: bigint;
  /** "now" in seconds — from the L2 block timestamp, never the local clock. */
  now: bigint;
  /** Skip when |next - current| <= this (feed units). */
  minDelta: bigint;
  /** Refuse relaying when the deviation exceeds this, in basis points. */
  maxJumpBps: bigint;
  /** Force a post when the on-chain reading reaches this age, seconds. */
  heartbeatAge: bigint;
}

export type Decision =
  | { action: "post"; reason: string }
  | { action: "skip"; reason: string } // deliberate skip → exit 2
  | { action: "refuse"; reason: string }; // guard refusal → exit 1

/**
 * Price-feed decision (XAU, UZS). The heartbeat check MUST come before the
 * unchanged early-return: an unchanged value still has to be republished when
 * the on-chain reading approaches its maxAge.
 */
export function decidePost(input: DecideInput): Decision {
  const { current, currentUpdatedAt, next, now, minDelta, maxJumpBps, heartbeatAge } = input;

  if (current > 0n) {
    const age = now - currentUpdatedAt;
    const delta = next > current ? next - current : current - next;
    if (delta <= minDelta) {
      if (age >= heartbeatAge) {
        return {
          action: "post",
          reason: `heartbeat: on-chain age ${age}s >= ${heartbeatAge}s, value unchanged (${current})`,
        };
      }
      return {
        action: "skip",
        reason: `unchanged (current=${current}, new=${next}, |Δ|=${delta} <= ε=${minDelta}, age ${age}s < ${heartbeatAge}s)`,
      };
    }
    const jumpBps = (delta * 10000n) / current;
    if (jumpBps > maxJumpBps) {
      return {
        action: "skip",
        reason: `wild deviation ${jumpBps}bps exceeds maxJumpBps=${maxJumpBps} (current=${current}, new=${next})`,
      };
    }
    return { action: "post", reason: `deviation ${jumpBps}bps within guard` };
  }

  return { action: "post", reason: "first post (no prior on-chain answer)" };
}

export interface DecideReserveInput {
  /** Current on-chain reserve in grams (0n = never posted). */
  current: bigint;
  currentUpdatedAt: bigint;
  /** New reserve from RESERVE_GRAMS. */
  next: bigint;
  /** "now" in seconds — from the L2 block timestamp. */
  now: bigint;
  /** Heartbeat age, seconds. */
  heartbeatAge: bigint;
  /** Guard: a change beyond this (basis points) needs RESERVE_CONFIRM. */
  maxJumpBps: bigint;
  /** Value of RESERVE_CONFIRM, if set — must equal `next` exactly to confirm. */
  confirm: string | undefined;
}

/**
 * Reserve decision. The reserve is the number that authorizes minting, so a
 * change beyond the guard is a REFUSAL (exit 1), not a skip: a typo in env
 * must not reach the chain automatically. Confirmed changes (RESERVE_CONFIRM
 * == exact new value) are deliberate and pass.
 */
export function decideReservePost(input: DecideReserveInput): Decision {
  const { current, currentUpdatedAt, next, now, heartbeatAge, maxJumpBps, confirm } = input;

  if (current === 0n) {
    return { action: "post", reason: "first reserve attestation (seed)" };
  }
  if (next === current) {
    const age = now - currentUpdatedAt;
    if (age >= heartbeatAge) {
      return {
        action: "post",
        reason: `heartbeat: on-chain age ${age}s >= ${heartbeatAge}s, reserve unchanged (${current}g)`,
      };
    }
    return {
      action: "skip",
      reason: `reserve unchanged (${current}g, age ${age}s < ${heartbeatAge}s)`,
    };
  }
  const delta = next > current ? next - current : current - next;
  const jumpBps = (delta * 10000n) / current;
  if (jumpBps > maxJumpBps) {
    if (confirm !== undefined && confirm === next.toString()) {
      return {
        action: "post",
        reason: `reserve change ${jumpBps}bps confirmed via RESERVE_CONFIRM (${current}g -> ${next}g)`,
      };
    }
    return {
      action: "refuse",
      reason:
        `reserve change ${jumpBps}bps exceeds maxJumpBps=${maxJumpBps} (${current}g -> ${next}g); ` +
        `refusing without RESERVE_CONFIRM=${next}`,
    };
  }
  return { action: "post", reason: `reserve change ${jumpBps}bps within guard (${current}g -> ${next}g)` };
}

export type SourceAgeVerdict =
  | { level: "ok" }
  | { level: "warn"; message: string }
  | { level: "refuse"; reason: string };

/**
 * Source-age guard for the Chainlink relay. `warnAge` sits above the source's
 * documented heartbeat (XAU/USD: 22h20m16s) so the log does not cry "market
 * closed" on an ordinary quiet weekday; `maxSourceAge` (default 72h, floor
 * 26h) separates "relay the last known value" from "source is broken".
 */
export function checkSourceAge(
  ageSeconds: bigint,
  maxSourceAge: bigint,
  warnAge: bigint,
): SourceAgeVerdict {
  if (ageSeconds > maxSourceAge) {
    return {
      level: "refuse",
      reason: `source broken: age ${ageSeconds}s > maxSourceAge ${maxSourceAge}s`,
    };
  }
  if (ageSeconds > warnAge) {
    return {
      level: "warn",
      message: `source heartbeat exceeded, relaying last known (age ${ageSeconds}s)`,
    };
  }
  return { level: "ok" };
}

/** Minimal provider shape for reading the block timestamp (mockable boundary). */
export interface BlockTimestampProvider {
  getBlock(tag: string): Promise<{ timestamp: number } | null>;
}

/** "now" from the chain, not from the local clock. */
export async function chainNowSeconds(
  provider: BlockTimestampProvider,
): Promise<bigint> {
  const block = await provider.getBlock("latest");
  if (!block) throw new Error("failed to fetch the latest block");
  return BigInt(block.timestamp);
}

/**
 * Parse a non-negative decimal string ("12048.84") into a scaled bigint at
 * `decimals` places, without floats. Throws on any other format or on a
 * fraction longer than `decimals` (silent precision loss is not acceptable
 * for a price).
 */
export function parseDecimalToScaledInt(raw: string, decimals: number): bigint {
  const m = /^(\d+)(?:\.(\d+))?$/.exec(raw.trim());
  if (!m || m[1] === undefined) {
    throw new Error(`not a non-negative decimal: ${JSON.stringify(raw)}`);
  }
  const intPart = m[1];
  const fracPart = m[2] ?? "";
  if (fracPart.length > decimals) {
    throw new Error(
      `fraction longer than ${decimals} decimals: ${JSON.stringify(raw)}`,
    );
  }
  return BigInt(intPart + fracPart.padEnd(decimals, "0"));
}

export interface CbuRate {
  /** Rate string as published, e.g. "12048.84" (sum per 1 USD). */
  rateRaw: string;
  /** Effective date string, "DD.MM.YYYY". */
  dateRaw: string;
}

/**
 * Validate the CBU JSON envelope. External input is untrusted: shape-check
 * before touching values (verified live 2026-07-23: array of objects with
 * string Rate and Date fields).
 */
export function parseCbuResponse(json: unknown): CbuRate {
  if (!Array.isArray(json) || json.length === 0) {
    throw new Error("CBU response is not a non-empty array");
  }
  const first: unknown = json[0];
  if (typeof first !== "object" || first === null) {
    throw new Error("CBU entry is not an object");
  }
  const entry = first as Record<string, unknown>;
  if (typeof entry.Rate !== "string" || typeof entry.Date !== "string") {
    throw new Error("CBU entry lacks string Rate/Date fields");
  }
  return { rateRaw: entry.Rate, dateRaw: entry.Date };
}

/**
 * Age of a CBU rate in whole days. `dateRaw` is the effective date
 * ("DD.MM.YYYY"); the API republishes the last business day over weekends, so
 * this guard catches a broken API (many days), never a weekend.
 */
export function cbuRateAgeDays(dateRaw: string, now: Date): number {
  const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(dateRaw.trim());
  if (!m) throw new Error(`CBU date is not DD.MM.YYYY: ${JSON.stringify(dateRaw)}`);
  const day = Number(m[1]);
  const month = Number(m[2]);
  const year = Number(m[3]);
  const rateUtc = Date.UTC(year, month - 1, day);
  const nowUtc = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return Math.floor((nowUtc - rateUtc) / 86_400_000);
}

/** Parse a strictly positive integer env value (RESERVE_GRAMS). */
export function parsePositiveInt(raw: string, name: string): bigint {
  const trimmed = raw.trim();
  if (!/^\d+$/.test(trimmed)) {
    throw new Error(`${name} is not a non-negative integer: ${JSON.stringify(raw)}`);
  }
  const v = BigInt(trimmed);
  if (v <= 0n) {
    throw new Error(`${name} must be positive, got ${trimmed}`);
  }
  return v;
}
