'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { api } from '@/lib/api';
import { AlertCircle, CheckCircle, Lock, Unlock, Gift, ChevronDown, ChevronUp } from 'lucide-react';

export default function StakingPage() {
  const { hapticFeedback } = useTelegram();
  const { t, language } = useTranslation();
  const queryClient = useQueryClient();

  const [amount, setAmount] = useState('');
  const [action, setAction] = useState<'deposit' | 'withdraw'>('deposit');
  const [success, setSuccess] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const { data: stakingData, isLoading } = useQuery({
    queryKey: ['staking'],
    queryFn: () => api.getStaking(),
    refetchInterval: 30000,
  });

  const { data: rewardsHistory } = useQuery({
    queryKey: ['stakingRewards'],
    queryFn: () => api.getStakingRewards(),
    enabled: showHistory,
  });

  const depositMutation = useMutation({
    mutationFn: (amount: number) => api.stakingDeposit(amount),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staking'] });
      queryClient.invalidateQueries({ queryKey: ['balances'] });
      setAmount('');
      setSuccess(t('depositSuccess'));
      hapticFeedback('success');
      setTimeout(() => setSuccess(null), 3000);
    },
    onError: () => hapticFeedback('error'),
  });

  const withdrawMutation = useMutation({
    mutationFn: (amount: number) => api.stakingWithdraw(amount),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staking'] });
      queryClient.invalidateQueries({ queryKey: ['balances'] });
      setAmount('');
      setSuccess(t('withdrawSuccess'));
      hapticFeedback('success');
      setTimeout(() => setSuccess(null), 3000);
    },
    onError: () => hapticFeedback('error'),
  });

  const stakingInfo = {
    apy: stakingData?.apy ? (stakingData.apy < 1 ? stakingData.apy * 100 : stakingData.apy) : 7,
    lockDays: 7,
    staked: parseFloat(stakingData?.balance || '0'),
    dailyReward: parseFloat(stakingData?.daily_reward || '0'),
    totalEarned: parseFloat(stakingData?.total_earned || '0'),
    isLocked: stakingData?.is_locked || false,
    lockedUntil: stakingData?.locked_until,
  };

  const handleAction = () => {
    if (!amount) return;
    const value = parseFloat(amount);

    if (action === 'deposit') {
      depositMutation.mutate(value);
    } else {
      withdrawMutation.mutate(value);
    }
  };

  const isPending = depositMutation.isPending || withdrawMutation.isPending;
  const error = depositMutation.error || withdrawMutation.error;

  const toggleHistory = () => {
    setShowHistory(!showHistory);
    hapticFeedback('selection');
  };

  const getLabel = (key: string) => {
    const labels: Record<string, Record<string, string>> = {
      totalEarned: { uz: 'Jami ishlab topilgan', ru: 'Всего заработано', en: 'Total Earned' },
      dailyReward: { uz: 'Kunlik daromad', ru: 'Дневной доход', en: 'Daily Reward' },
      rewardsHistory: { uz: 'Mukofotlar tarixi', ru: 'История наград', en: 'Rewards History' },
      noRewards: { uz: 'Hali mukofotlar yo\'q', ru: 'Пока нет наград', en: 'No rewards yet' },
    };
    return labels[key]?.[language] || labels[key]?.['en'] || key;
  };

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">{t('staking')}</h1>

      {/* APY card */}
      <div className="bg-gold/10 border-2 border-gold rounded-xl p-4 text-center">
        <div className="text-text-muted text-sm">{t('annualYield')}</div>
        <div className="text-4xl font-bold text-gold">{Math.round(stakingInfo.apy)}% APY</div>
        <div className="text-text-muted text-xs mt-1">{stakingInfo.lockDays} {t('lockPeriod')}</div>
      </div>

      {/* Success message */}
      {success && (
        <div className="bg-green/10 border border-green rounded-xl p-3 flex items-center gap-2">
          <CheckCircle size={20} className="text-green" />
          <span className="text-green text-sm">{success}</span>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="bg-red/10 border border-red rounded-xl p-3 flex items-center gap-2">
          <AlertCircle size={20} className="text-red" />
          <span className="text-red text-sm">{(error as Error)?.message}</span>
        </div>
      )}

      {/* Staking stats */}
      <div className="bg-card rounded-xl p-4 space-y-3 border border-border">
        {isLoading ? (
          <div className="flex justify-center py-4">
            <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-gold" />
          </div>
        ) : (
          <>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">{t('staked')}</span>
              <span className="font-semibold">{stakingInfo.staked.toFixed(4)} OLTIN</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">{getLabel('dailyReward')}</span>
              <span className="font-semibold text-gold">+{stakingInfo.dailyReward.toFixed(6)} OLTIN</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted flex items-center gap-1">
                <Gift size={14} /> {getLabel('totalEarned')}
              </span>
              <span className="font-semibold text-green">+{stakingInfo.totalEarned.toFixed(6)} OLTIN</span>
            </div>
            {stakingInfo.isLocked && stakingInfo.lockedUntil && (
              <div className="flex justify-between items-center text-sm">
                <span className="text-text-muted flex items-center gap-1">
                  <Lock size={14} /> {t('lockedUntil')}
                </span>
                <span className="text-gold">
                  {new Date(stakingInfo.lockedUntil).toLocaleDateString()}
                </span>
              </div>
            )}
            {!stakingInfo.isLocked && stakingInfo.staked > 0 && (
              <div className="flex items-center gap-1 text-green text-sm">
                <Unlock size={14} /> {t('unlocked')}
              </div>
            )}
          </>
        )}
      </div>

      {/* Rewards History */}
      <div className="bg-card rounded-xl overflow-hidden border border-border">
        <button
          onClick={toggleHistory}
          className="w-full p-4 flex items-center justify-between text-left"
        >
          <span className="font-medium">{getLabel('rewardsHistory')}</span>
          {showHistory ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>

        {showHistory && (
          <div className="border-t border-border">
            {!rewardsHistory || rewardsHistory.length === 0 ? (
              <div className="p-4 text-center text-text-muted text-sm">
                {getLabel('noRewards')}
              </div>
            ) : (
              <div className="divide-y divide-border">
                {rewardsHistory.slice(0, 10).map((reward: any, index: number) => (
                  <div key={index} className="p-3 flex justify-between items-center">
                    <span className="text-text-muted text-sm">
                      {new Date(reward.date).toLocaleDateString()}
                    </span>
                    <span className="text-green font-medium">
                      +{parseFloat(reward.amount).toFixed(6)} OLTIN
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action toggle */}
      <div className="flex bg-card rounded-xl p-1 border border-border">
        <button
          onClick={() => { setAction('deposit'); hapticFeedback('selection'); }}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
            action === 'deposit' ? 'bg-gold text-background' : 'text-text-muted'
          }`}
        >
          {t('deposit')}
        </button>
        <button
          onClick={() => { setAction('withdraw'); hapticFeedback('selection'); }}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
            action === 'withdraw' ? 'bg-gold text-background' : 'text-text-muted'
          }`}
          disabled={stakingInfo.isLocked}
        >
          {t('withdraw')}
        </button>
      </div>

      {/* Amount input */}
      <div className="bg-card rounded-xl p-4 space-y-3 border border-border">
        <label className="text-text-muted text-sm">
          {action === 'deposit' ? t('depositAmount') : t('withdrawAmount')}
        </label>
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.0000"
          className="w-full bg-background border border-border rounded-xl px-4 py-3 text-xl focus:outline-none focus:border-gold"
        />
        {action === 'withdraw' && (
          <button
            onClick={() => setAmount(stakingInfo.staked.toString())}
            className="text-gold text-sm"
          >
            Max: {stakingInfo.staked.toFixed(4)} OLTIN
          </button>
        )}
      </div>

      {/* Submit button */}
      <button
        onClick={handleAction}
        disabled={!amount || isPending || (action === 'withdraw' && stakingInfo.isLocked)}
        className="w-full bg-gold text-background py-4 rounded-xl font-semibold disabled:opacity-50"
      >
        {isPending ? '...': action === 'deposit' ? t('stake') : t('withdraw')}
      </button>

      <div className="text-text-muted text-xs text-center">{t('rewardsInfo')}</div>
    </div>
  );
}
