'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatUnits } from 'viem';
import { AlertCircle, CheckCircle, Lock, Loader2, Gift } from 'lucide-react';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { useBalances } from '@/hooks/useBalances';
import { api } from '@/lib/api';
import {
  approveStakingForOltin,
  stake,
  unstake,
  claimStakingReward,
  publicClient,
} from '@/lib/chain';
import { formatToken, parseTokenAmount } from '@/lib/format';
import { deriveStakingView } from '@/lib/staking';
import { useWalletStore } from '@/stores/wallet';
import type { StakingInfoResponse } from '@/types';

const TOKEN_DECIMALS = 18;
const RECEIPT_TIMEOUT_MS = 60_000;

// Zero position — shown while loading or when the wallet has no stake yet
// (GET /staking 400s on an un-onboarded wallet; we render zeros, not an error).
const EMPTY_STAKING: StakingInfoResponse = {
  wallet_address: '',
  total_principal_wei: '0',
  unlocked_wei: '0',
  pending_reward_wei: '0',
  lot_count: 0,
  next_unlock_at: 0,
  apy_bps: 700,
  lock_period_days: 7,
};

export default function StakingPage() {
  const { hapticFeedback } = useTelegram();
  const { t, language } = useTranslation();
  const queryClient = useQueryClient();
  const account = useWalletStore((s) => s.account);

  const [amount, setAmount] = useState('');
  const [action, setAction] = useState<'deposit' | 'withdraw'>('deposit');
  const [success, setSuccess] = useState<string | null>(null);
  const [step, setStep] = useState<null | 'approving' | 'staking'>(null);

  const L = (uz: string, ru: string, en: string) =>
    language === 'uz' ? uz : language === 'ru' ? ru : en;

  // Read-only on-chain position. 400 (no wallet yet) falls through to the empty
  // position below, never a failure banner.
  const { data: stakingData } = useQuery({
    queryKey: ['staking'],
    queryFn: () => api.getStaking(),
    retry: false,
    refetchInterval: 30000,
  });
  const { data: balancesData } = useBalances();

  const view = deriveStakingView(stakingData ?? EMPTY_STAKING);
  const oltinWei = balancesData ? BigInt(balancesData.wallet.oltin_wei) : BigInt(0);

  const flash = (message: string) => {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 3000);
  };
  const invalidate = () => {
    // stake/unstake/claim move OLTIN, so the balance AND the on-chain history
    // (indexer-backed) both change — refresh all three.
    queryClient.invalidateQueries({ queryKey: ['staking'] });
    queryClient.invalidateQueries({ queryKey: ['balances'] });
    queryClient.invalidateQueries({ queryKey: ['transactions'] });
  };
  const msg = (e: unknown) => (e instanceof Error ? e.message : String(e));

  // Map an on-chain error to a localized message. `afterApprove` marks the
  // stake leg, where approve gas was already spent before the revert.
  const explain = (raw: string, afterApprove: boolean): string => {
    if (/insufficient funds|exceeds the balance/i.test(raw)) {
      return L('Gaz uchun ETH yetarli emas', 'Недостаточно ETH на газ', 'Not enough ETH for gas');
    }
    if (/insufficient unlocked|insufficient principal/i.test(raw)) {
      return L('Mablag hali bloklangan', 'Средства ещё заблокированы', 'Funds are still locked');
    }
    return afterApprove
      ? L('Amal rad etildi (approve sarflandi)', 'Операция отклонена (approve потрачен)', 'Reverted (approve spent)')
      : L('Tranzaksiya yuborilmadi', 'Транзакция не отправлена', 'Transaction failed');
  };

  const stakeMutation = useMutation({
    mutationFn: async () => {
      if (!account) throw new Error(L('Hamyon qulflangan', 'Кошелёк заблокирован', 'Wallet is locked'));
      const amt = parseTokenAmount(amount, TOKEN_DECIMALS);
      if (amt === null) throw new Error(L('Notogri summa', 'Неверная сумма', 'Invalid amount'));
      if (amt > oltinWei) {
        throw new Error(L('OLTIN yetarli emas', 'Недостаточно OLTIN', 'Insufficient OLTIN'));
      }

      // Step 1 — approve the staking contract to pull OLTIN.
      setStep('approving');
      let approveHash: `0x${string}`;
      try {
        approveHash = await approveStakingForOltin(account, amt);
      } catch (err) {
        throw new Error(explain(msg(err), false));
      }
      const ar = await publicClient.waitForTransactionReceipt({ hash: approveHash, timeout: RECEIPT_TIMEOUT_MS });
      if (ar.status !== 'success') {
        throw new Error(L('Approve rad etildi', 'Approve отклонён', 'Approve reverted'));
      }

      // Step 2 — stake. From here a revert means approve gas was already spent.
      setStep('staking');
      let stakeHash: `0x${string}`;
      try {
        stakeHash = await stake(account, amt);
      } catch (err) {
        throw new Error(explain(msg(err), true));
      }
      const sr = await publicClient.waitForTransactionReceipt({ hash: stakeHash, timeout: RECEIPT_TIMEOUT_MS });
      if (sr.status !== 'success') throw new Error(explain('reverted', true));
      return stakeHash;
    },
    onSuccess: () => {
      invalidate();
      setAmount('');
      flash(t('depositSuccess'));
      hapticFeedback('success');
    },
    onError: () => hapticFeedback('error'),
    onSettled: () => setStep(null),
  });

  const withdrawMutation = useMutation({
    mutationFn: async () => {
      if (!account) throw new Error(L('Hamyon qulflangan', 'Кошелёк заблокирован', 'Wallet is locked'));
      const amt = parseTokenAmount(amount, TOKEN_DECIMALS);
      if (amt === null) throw new Error(L('Notogri summa', 'Неверная сумма', 'Invalid amount'));
      // Only unlocked principal can be withdrawn; the contract reverts otherwise.
      if (amt > BigInt(view.unlockedWei)) {
        throw new Error(L('Ochiq mablagdan oshdi', 'Больше разблокированного', 'Exceeds unlocked'));
      }
      let hash: `0x${string}`;
      try {
        hash = await unstake(account, amt);
      } catch (err) {
        throw new Error(explain(msg(err), false));
      }
      const r = await publicClient.waitForTransactionReceipt({ hash, timeout: RECEIPT_TIMEOUT_MS });
      if (r.status !== 'success') throw new Error(explain('reverted', false));
      return hash;
    },
    onSuccess: () => {
      invalidate();
      setAmount('');
      flash(t('withdrawSuccess'));
      hapticFeedback('success');
    },
    onError: () => hapticFeedback('error'),
  });

  const claimMutation = useMutation({
    mutationFn: async () => {
      if (!account) throw new Error(L('Hamyon qulflangan', 'Кошелёк заблокирован', 'Wallet is locked'));
      let hash: `0x${string}`;
      try {
        hash = await claimStakingReward(account);
      } catch (err) {
        throw new Error(explain(msg(err), false));
      }
      const r = await publicClient.waitForTransactionReceipt({ hash, timeout: RECEIPT_TIMEOUT_MS });
      if (r.status !== 'success') throw new Error(explain('reverted', false));
      return hash;
    },
    onSuccess: () => {
      invalidate();
      // No amount claimed is asserted here — claim() pays min(owed, rewardPool),
      // so the paid figure is only known after the balance refetches.
      flash(L('Sorov yuborildi', 'Заявка отправлена', 'Claim submitted'));
      hapticFeedback('success');
    },
    onError: () => hapticFeedback('error'),
  });

  const busy = stakeMutation.isPending || withdrawMutation.isPending || claimMutation.isPending;
  const error = stakeMutation.error || withdrawMutation.error || claimMutation.error;

  const handleSubmit = () => {
    if (!amount) return;
    if (action === 'deposit') stakeMutation.mutate();
    else withdrawMutation.mutate();
  };

  const maxWei = action === 'deposit' ? oltinWei : BigInt(view.unlockedWei);

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">{t('staking')}</h1>

      {/* APY card */}
      <div className="bg-gold/10 border-2 border-gold rounded-xl p-4 text-center">
        <div className="text-text-muted text-sm">{t('annualYield')}</div>
        <div className="text-4xl font-bold text-gold">{view.apyPercent}% APY</div>
        <div className="text-text-muted text-xs mt-1">{view.lockPeriodDays} {t('lockPeriod')}</div>
      </div>

      {/* Success / error */}
      {success && (
        <div className="bg-green/10 border border-green rounded-xl p-3 flex items-center gap-2">
          <CheckCircle size={20} className="text-green" />
          <span className="text-green text-sm">{success}</span>
        </div>
      )}
      {error && (
        <div className="bg-red/10 border border-red rounded-xl p-3 flex items-center gap-2">
          <AlertCircle size={20} className="text-red" />
          <span className="text-red text-sm">{(error as Error)?.message}</span>
        </div>
      )}

      {/* Position */}
      <div className="bg-card rounded-xl p-4 space-y-3 border border-border">
        <div className="flex justify-between items-center">
          <span className="text-text-muted">{t('staked')}</span>
          <span className="font-semibold">{view.principal} OLTIN</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-text-muted">{t('unlocked')}</span>
          <span className="font-semibold">{view.unlocked} OLTIN</span>
        </div>
        {view.isLocked && view.nextUnlockAt > 0 && (
          <div className="flex justify-between items-center text-sm">
            <span className="text-text-muted flex items-center gap-1">
              <Lock size={14} /> {L('Yaqin ochilish', 'Ближайшая разблокировка', 'Nearest unlock')}
            </span>
            <span className="text-gold">
              {new Date(view.nextUnlockAt * 1000).toLocaleDateString()}
            </span>
          </div>
        )}

        {/* Pending reward + claim */}
        <div className="flex justify-between items-center pt-1 border-t border-border">
          <span className="text-text-muted flex items-center gap-1">
            <Gift size={14} /> {L('Mukofot', 'Награда', 'Reward')}
          </span>
          <span className="font-semibold text-green">+{view.pending} OLTIN</span>
        </div>
        <button
          onClick={() => claimMutation.mutate()}
          disabled={!view.claimable || busy}
          className="w-full rounded-xl py-2.5 text-sm font-medium bg-green/15 text-green border border-green/40 disabled:opacity-40 flex items-center justify-center gap-2"
        >
          {claimMutation.isPending ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              {L('Yuborilmoqda…', 'Отправка…', 'Claiming…')}
            </>
          ) : view.claimable ? (
            L('Mukofotni olish', 'Получить награду', 'Claim reward')
          ) : (
            L('Mukofot hali yigilmadi', 'Награда ещё не накопилась', 'Reward not yet accrued')
          )}
        </button>
      </div>

      {/* Action toggle */}
      <div className="flex bg-card rounded-xl p-1 border border-border">
        <button
          onClick={() => { setAction('deposit'); setAmount(''); hapticFeedback('selection'); }}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
            action === 'deposit' ? 'bg-gold text-background' : 'text-text-muted'
          }`}
        >
          {t('deposit')}
        </button>
        <button
          onClick={() => { setAction('withdraw'); setAmount(''); hapticFeedback('selection'); }}
          disabled={!view.withdrawable}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-40 ${
            action === 'withdraw' ? 'bg-gold text-background' : 'text-text-muted'
          }`}
        >
          {t('withdraw')}
        </button>
      </div>

      {/* Amount input */}
      <div className="bg-card rounded-xl p-4 space-y-3 border border-border">
        <div className="flex justify-between items-center">
          <label className="text-text-muted text-sm">
            {action === 'deposit' ? t('depositAmount') : t('withdrawAmount')}
          </label>
          <button
            onClick={() => setAmount(formatUnits(maxWei, TOKEN_DECIMALS))}
            className="text-gold text-sm"
          >
            {L('Bor', 'Доступно', 'Available')}: {formatToken(maxWei.toString())} OLTIN
          </button>
        </div>
        <input
          type="number"
          inputMode="decimal"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.0000"
          className="w-full bg-background border border-border rounded-xl px-4 py-3 text-xl focus:outline-none focus:border-gold"
        />
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!amount || busy || (action === 'withdraw' && !view.withdrawable)}
        className="w-full bg-gold text-background py-4 rounded-xl font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {stakeMutation.isPending || withdrawMutation.isPending ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            {step === 'approving'
              ? L('Ruxsat berilmoqda…', 'Разрешение…', 'Approving…')
              : action === 'deposit'
                ? L('Steyking…', 'Стейкинг…', 'Staking…')
                : L('Chiqarilmoqda…', 'Вывод…', 'Withdrawing…')}
          </>
        ) : action === 'deposit' ? (
          t('stake')
        ) : (
          t('withdraw')
        )}
      </button>

      <div className="text-text-muted text-xs text-center">{t('rewardsInfo')}</div>
    </div>
  );
}
