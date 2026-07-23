/**
 * Shared keeper logic: the post/skip decision, extracted so it can be unit
 * tested without RPC or a chain. Keepers are thin scripts over this module.
 *
 * Exit code contract (used by cron alerting in P4-A):
 *   0 = posted, 2 = deliberate skip, 1 = refusal/error.
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
  | { action: "skip"; reason: string };

export function decidePost(input: DecideInput): Decision {
  const { current, next, minDelta, maxJumpBps } = input;

  if (current > 0n) {
    const delta = next > current ? next - current : current - next;
    if (delta <= minDelta) {
      return {
        action: "skip",
        reason: `unchanged (current=${current}, new=${next}, |Δ|=${delta} <= ε=${minDelta})`,
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
