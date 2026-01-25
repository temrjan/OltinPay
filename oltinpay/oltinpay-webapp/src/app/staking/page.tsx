'use client';

import { useState } from 'react';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';

export default function StakingPage() {
  const { hapticFeedback } = useTelegram();
  const { t } = useTranslation();
  const [amount, setAmount] = useState('');

  const stakingInfo = { apy: 7, lockDays: 7, staked: 0, rewards: 0 };

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">{t('staking')}</h1>

      <div className="bg-gold/10 border border-gold rounded-xl p-4 text-center">
        <div className="text-text-muted text-sm">{t('annualYield')}</div>
        <div className="text-4xl font-bold text-gold">{stakingInfo.apy}% APY</div>
        <div className="text-text-muted text-xs mt-1">{stakingInfo.lockDays} {t('lockPeriod')}</div>
      </div>

      <div className="bg-card rounded-xl p-4 space-y-3">
        <div className="flex justify-between">
          <span className="text-text-muted">{t('staked')}</span>
          <span className="font-semibold">{stakingInfo.staked.toFixed(4)} OLTIN</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">{t('rewards')}</span>
          <span className="font-semibold text-green">{stakingInfo.rewards.toFixed(6)} OLTIN</span>
        </div>
      </div>

      <div className="bg-card rounded-xl p-4 space-y-3">
        <label className="text-text-muted text-sm">{t('stake')}</label>
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.0000"
          className="w-full bg-background border border-border rounded-xl px-4 py-3 text-xl focus:outline-none focus:border-gold"
        />
      </div>

      <button
        onClick={() => hapticFeedback('medium')}
        disabled={!amount}
        className="w-full bg-gold text-background py-4 rounded-xl font-semibold disabled:opacity-50"
      >
        {t('stake')}
      </button>

      <div className="text-text-muted text-xs text-center">{t('rewardsInfo')}</div>
    </div>
  );
}
