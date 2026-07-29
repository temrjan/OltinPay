import { formatToken } from './format';
import type { StakingInfoResponse } from '@/types';

/**
 * Minimum pending reward the claim button unlocks at: 0.0001 OLTIN = 1e14 wei.
 *
 * The reward accrues per second, so `pending > 0` is true within a second of
 * staking — gating on that would let the user pay gas for a payout too small to
 * change the visible OLTIN balance (printed at 4 decimals). Tie the gate to that
 * display precision instead, so a claim always produces a visible change.
 * (BigInt literals are unavailable at this TS target — use BigInt('…').)
 */
export const CLAIM_MIN_WEI = BigInt('100000000000000');

export interface StakingView {
  /** Any staked principal at all. */
  hasPosition: boolean;
  /** Formatted for display (4 dp), from raw wei. */
  principal: string;
  unlocked: string;
  /** Reward is tiny — show 8 dp so it is not rounded to 0. */
  pending: string;
  /** Raw unlocked wei — the withdraw cap (never the full principal). */
  unlockedWei: string;
  apyPercent: number;
  /** Some principal is still time-locked (unlocked < principal). */
  isLocked: boolean;
  /** There is unlocked principal to withdraw. */
  withdrawable: boolean;
  /** Pending reward is large enough to make a visible claim. */
  claimable: boolean;
  /** Nearest lot unlock (unix seconds); 0 when nothing is locked. */
  nextUnlockAt: number;
  lockPeriodDays: number;
}

/**
 * Derive the staking screen's view model from the raw on-chain position
 * (GET /staking). Pure — no clock, no I/O — so it is unit-testable; the screen
 * formats `nextUnlockAt` into a date itself.
 */
export function deriveStakingView(info: StakingInfoResponse): StakingView {
  const principalWei = BigInt(info.total_principal_wei);
  const unlockedWei = BigInt(info.unlocked_wei);
  const pendingWei = BigInt(info.pending_reward_wei);

  return {
    hasPosition: principalWei > BigInt(0),
    principal: formatToken(info.total_principal_wei),
    unlocked: formatToken(info.unlocked_wei),
    pending: formatToken(info.pending_reward_wei, 8),
    unlockedWei: info.unlocked_wei,
    apyPercent: info.apy_bps / 100,
    isLocked: unlockedWei < principalWei,
    withdrawable: unlockedWei > BigInt(0),
    claimable: pendingWei >= CLAIM_MIN_WEI,
    nextUnlockAt: info.next_unlock_at,
    lockPeriodDays: info.lock_period_days,
  };
}
