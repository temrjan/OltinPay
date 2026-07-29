import { describe, it, expect } from 'vitest';
import { deriveStakingView, CLAIM_MIN_WEI } from './staking';
import type { StakingInfoResponse } from '@/types';

// 18-decimal helpers (avoid BigInt literals — unavailable at this TS target).
const OLTIN = (n: string) => (BigInt(n) * BigInt('1000000000000000000')).toString();

function mk(overrides: Partial<StakingInfoResponse> = {}): StakingInfoResponse {
  return {
    wallet_address: '0xabc',
    total_principal_wei: '0',
    unlocked_wei: '0',
    pending_reward_wei: '0',
    lot_count: 0,
    next_unlock_at: 0,
    apy_bps: 700,
    lock_period_days: 7,
    ...overrides,
  };
}

describe('deriveStakingView', () => {
  it('reports no position when nothing is staked', () => {
    const v = deriveStakingView(mk());
    expect(v.hasPosition).toBe(false);
    expect(v.isLocked).toBe(false);
    expect(v.withdrawable).toBe(false);
  });

  it('is fully locked when principal is staked but nothing is unlocked', () => {
    const v = deriveStakingView(
      mk({ total_principal_wei: OLTIN('100'), unlocked_wei: '0', lot_count: 1, next_unlock_at: 1785906424 }),
    );
    expect(v.hasPosition).toBe(true);
    expect(v.isLocked).toBe(true);
    expect(v.withdrawable).toBe(false);
    expect(v.unlockedWei).toBe('0'); // withdraw cap is unlocked, not principal
    expect(v.nextUnlockAt).toBe(1785906424);
  });

  it('is partially unlocked when unlocked < principal', () => {
    const v = deriveStakingView(
      mk({ total_principal_wei: OLTIN('100'), unlocked_wei: OLTIN('50'), lot_count: 2 }),
    );
    expect(v.isLocked).toBe(true); // 50 still locked
    expect(v.withdrawable).toBe(true);
    expect(v.unlockedWei).toBe(OLTIN('50'));
  });

  it('is not locked when all principal is unlocked', () => {
    const v = deriveStakingView(
      mk({ total_principal_wei: OLTIN('100'), unlocked_wei: OLTIN('100'), lot_count: 1 }),
    );
    expect(v.isLocked).toBe(false);
    expect(v.withdrawable).toBe(true);
  });

  it('gates claim on the 0.0001 OLTIN display threshold, not > 0 wei', () => {
    // 1 wei of pending is > 0 but invisible at 4-dp balance precision.
    expect(deriveStakingView(mk({ pending_reward_wei: '1' })).claimable).toBe(false);
    // Just below the threshold (5e13 < 1e14).
    expect(deriveStakingView(mk({ pending_reward_wei: '50000000000000' })).claimable).toBe(false);
    // Exactly at the threshold (1e14 = 0.0001 OLTIN).
    expect(deriveStakingView(mk({ pending_reward_wei: CLAIM_MIN_WEI.toString() })).claimable).toBe(true);
  });

  it('converts apy_bps to a percentage', () => {
    expect(deriveStakingView(mk({ apy_bps: 700 })).apyPercent).toBe(7);
  });

  it('formats pending at 8 dp so a tiny reward is not rounded to 0', () => {
    // 0.0002301 OLTIN = 2.301e14 wei — would render as "0" at the default 4 dp.
    const v = deriveStakingView(mk({ pending_reward_wei: '230100000000000' }));
    expect(v.pending).toBe('0.0002301');
  });
});
