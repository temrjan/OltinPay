/**
 * Single source of truth for the OltinPaymaster deployment configuration.
 *
 * The deploy script and BOTH test suites import these. Do not re-declare the
 * literals anywhere: the plain-EVM suite, the zkSync VM suite and the live
 * deployment must be provably the same configuration, not three copies kept in
 * step by a comment.
 *
 * The numbers are anchored on measurements, not taste:
 *   ETH ~ $1922, OLTIN (1 g of gold) ~ $106  =>  ~18 OLTIN per ETH.
 *   A real sponsored ERC20 transfer measured on the zkSync VM prefunds
 *   ~1.4e13 wei of gas, i.e. ~0.00026 OLTIN ~ $0.03 at this rate.
 */

/** OLTIN (18 dec) charged per 1 ETH of sponsored gas, at deployment. */
export const RATE = 18_000_000_000_000_000_000n; // 18e18

/** Immutable rate bounds — a span of x100 around the deployment rate, so only
 *  a fat finger (or `rate = 0`, which would make this a free relay) is refused,
 *  not a real market move. */
export const MIN_RATE = 1_800_000_000_000_000_000n; // rate / 10
export const MAX_RATE = 180_000_000_000_000_000_000n; // rate * 10

/** Sponsorship stops when the rate is older than this. */
export const MAX_RATE_AGE = 30n * 24n * 60n * 60n; // 30 days

/** Surcharge on top of the pegged fee. */
export const SURCHARGE_BPS = 300n; // 3%

/** Absolute fee floor. Deliberately ~26x BELOW the pegged fee of a typical
 *  transaction (measured: 2.5868e14 vs this 1e13): the peg must price gas, or
 *  the fee is a constant and the peg is decoration. */
export const MIN_FEE_OLTIN = 10_000_000_000_000n; // 1e13 = 0.00001 OLTIN

/** Spending ceilings, in wei of sponsored ETH. */
export const PER_TX_CAP = 500_000_000_000_000n; // 5e14 = 0.0005 ETH
// Equal to PER_TX_CAP on purpose: with a sender cap of 2e15 against a 5e15
// global cap, THREE fresh addresses could exhaust the whole day's sponsorship
// for everyone (~$10 of OLTIN). At 5e14 a legitimate user still gets ~35
// transactions a day and a griefer needs ten addresses.
export const SENDER_DAILY_CAP = 500_000_000_000_000n; // 5e14 = 0.0005 ETH
export const GLOBAL_DAILY_CAP = 5_000_000_000_000_000n; // 5e15 = 0.005 ETH

/** Constructor arguments in order, for deployment and for the test fixtures. */
export function paymasterArgs(oltinToken: string) {
  return [
    oltinToken,
    MIN_RATE,
    MAX_RATE,
    MAX_RATE_AGE,
    RATE,
    SURCHARGE_BPS,
    MIN_FEE_OLTIN,
    PER_TX_CAP,
    SENDER_DAILY_CAP,
    GLOBAL_DAILY_CAP,
  ] as const;
}

/** A representative sponsored transaction, measured on the zkSync VM. Used by
 *  the plain-EVM suite as its reference transaction and by the deploy script's
 *  "the peg, not the floor, prices this" sanity check. */
export const SAMPLE_GAS_LIMIT = 308_343n;
export const SAMPLE_MAX_FEE_PER_GAS = 45_250_000n;
