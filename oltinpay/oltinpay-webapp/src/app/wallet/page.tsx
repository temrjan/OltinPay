'use client';

import { useState } from 'react';
import { ArrowUpRight, ArrowDownLeft, RefreshCw, AlertCircle, Gift, Check, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { useBalances } from '@/hooks/useBalances';
import { useTransactions } from '@/hooks/useTransactions';
import { api } from '@/lib/api';
import { formatToken } from '@/lib/format';
import { prepareHistory } from '@/lib/history';
import type { DisplayTx } from '@/lib/history';
import { useAppStore } from '@/stores/app';

type AccountType = 'wallet' | 'staking';

export default function WalletPage() {
  const { user: tgUser, hapticFeedback } = useTelegram();
  const { t, language } = useTranslation();
  const user = useAppStore((state) => state.user);
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<AccountType>('wallet');
  const [agreed, setAgreed] = useState(false);

  const { data: balancesData, isLoading, error, refetch } = useBalances();

  // Real on-chain history (indexer-backed). Errors/400 (no wallet yet) fall
  // through to the empty state below, never a failure toast.
  const { data: transactionsData } = useTransactions();

  const { data: welcomeStatus } = useQuery({
    queryKey: ['welcome-status'],
    queryFn: () => api.getWelcomeStatus(),
    staleTime: 30000,
  });

  const claimMutation = useMutation({
    mutationFn: () => api.claimWelcome(),
    onSuccess: () => {
      hapticFeedback('medium');
      queryClient.invalidateQueries({ queryKey: ['welcome-status'] });
      queryClient.invalidateQueries({ queryKey: ['balances'] });
      queryClient.invalidateQueries({ queryKey: ['transfers'] });
    },
    onError: () => {
      // A 409 (already claimed / receipt-timeout reconciliation) means a claim
      // now exists — refetch status so the card reflects reality rather than
      // offering a retry that would just 409 again.
      queryClient.invalidateQueries({ queryKey: ['welcome-status'] });
    },
  });

  // On-chain balances are raw wei strings — format for display (native tokens,
  // there is no USD in the /balances schema).
  const walletUzd = balancesData ? formatToken(balancesData.wallet.uzd_wei) : '0';
  const walletOltin = balancesData ? formatToken(balancesData.wallet.oltin_wei) : '0';
  const stakedOltin = balancesData
    ? formatToken(balancesData.staking.total_principal_wei)
    : '0';

  const tabs = [
    { id: 'wallet', label: t('wallet') },
    { id: 'staking', label: t('staking') },
  ] as const;

  const displayName = user?.oltin_id?.startsWith('user_')
    ? tgUser?.first_name || 'User'
    : `@${user?.oltin_id}`;

  // Rows shown for the active tab.
  const balanceRows =
    activeTab === 'wallet'
      ? [
          { label: 'UZD', value: walletUzd },
          { label: 'OLTIN', value: walletOltin },
        ]
      : [{ label: 'OLTIN', value: stakedOltin }];

  // On-chain history: correct token symbol + collapsed mint/burn double-records.
  const L = (uz: string, ru: string, en: string) =>
    language === 'uz' ? uz : language === 'ru' ? ru : en;
  const history = prepareHistory(transactionsData ?? []);
  const kindLabel = (kind: DisplayTx['kind']): string => {
    switch (kind) {
      case 'received':
        return t('received');
      case 'sent':
        return t('sent');
      case 'minted':
        return L('Berildi', 'Начислено', 'Credited');
      case 'burned':
        return L('Yechildi', 'Списано', 'Debited');
      case 'self':
        return L("O'ziga", 'Себе', 'Self');
    }
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-text-muted text-sm">{t('welcome')}</div>
          <div className="text-xl font-semibold">{displayName}</div>
        </div>
        <button
          onClick={() => { refetch(); hapticFeedback('medium'); }}
          className="p-2 rounded-full bg-card border border-border"
          disabled={isLoading}
        >
          <RefreshCw size={20} className={isLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red/10 border border-red rounded-xl p-3 flex items-center gap-2">
          <AlertCircle size={20} className="text-red" />
          <span className="text-red text-sm">{t('errorLoading')}</span>
        </div>
      )}

      {/* Total Balance Card */}
      <div className="bg-gradient-to-br from-gold/20 to-gold/5 rounded-2xl p-5 border-2 border-gold text-center">
        {isLoading ? (
          <div className="h-9 flex items-center justify-center">
            <div className="animate-pulse bg-gold/20 rounded h-8 w-32" />
          </div>
        ) : (
          <div className="text-3xl font-bold text-gold">
            {walletUzd} <span className="text-xl">UZD</span>
          </div>
        )}
        <div className="text-text-muted text-sm mt-1">{t('totalBalance')}</div>
      </div>

      {/* Demo Balance (welcome bonus) — shown until claimed */}
      {welcomeStatus && !welcomeStatus.claimed && (
        <div className="bg-gradient-to-b from-gold/10 to-gold/5 border border-gold/30 rounded-xl p-4 space-y-3">
          <div className="flex gap-3">
            <div className="w-10 h-10 rounded-xl bg-gold/20 flex items-center justify-center shrink-0">
              <Gift size={20} className="text-gold" />
            </div>
            <div>
              <h3 className="font-semibold flex items-center gap-2">
                {t('demoBalanceTitle')}
                <span className="text-[10px] tracking-wider font-bold text-gold border border-gold/50 rounded px-1.5 py-px">
                  {t('demoBadge')}
                </span>
              </h3>
              <p className="text-text-muted text-sm mt-1">{t('demoBalanceSubtitle')}</p>
            </div>
          </div>

          <label className="flex gap-2.5 items-start bg-card border border-border rounded-xl p-3 cursor-pointer focus-within:ring-2 focus-within:ring-gold/60">
            <input
              type="checkbox"
              className="sr-only"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
            />
            <span
              className={`shrink-0 mt-0.5 w-5 h-5 rounded-md border-[1.5px] flex items-center justify-center transition-colors ${
                agreed
                  ? 'bg-gold border-gold text-background'
                  : 'border-border bg-background text-transparent'
              }`}
            >
              <Check size={13} strokeWidth={3.5} />
            </span>
            <span className="text-sm leading-snug">{t('demoBalanceDisclaimer')}</span>
          </label>

          {claimMutation.isError && (
            <div className="flex items-center gap-2 text-red text-sm">
              <AlertCircle size={16} className="shrink-0" />
              {/* Never surface the raw API `detail` here — FastAPI always sends
                  a non-empty, unlocalized string (e.g. "KEY_BANK_OPS is not
                  configured on the server"). Show the localized message only. */}
              <span>{t('demoBalanceError')}</span>
            </div>
          )}

          <button
            onClick={() => {
              hapticFeedback('medium');
              claimMutation.mutate();
            }}
            disabled={!agreed || claimMutation.isPending}
            className="w-full rounded-xl py-3.5 font-semibold flex items-center justify-center gap-2 bg-gold text-background transition-colors disabled:bg-gold/20 disabled:text-text-muted"
          >
            {claimMutation.isPending ? (
              <>
                <Loader2 size={17} className="animate-spin" />
                {t('demoBalanceClaiming')}
              </>
            ) : (
              t('demoBalanceGet')
            )}
          </button>
        </div>
      )}

      {/* Account Tabs */}
      <div className="flex bg-card rounded-xl p-1 border border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); hapticFeedback('selection'); }}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-gold text-background'
                : 'text-text-muted'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Account Balances */}
      <div className="bg-card rounded-xl p-4 space-y-3 border border-border">
        {balanceRows.map((row) => (
          <div key={row.label} className="flex justify-between items-center">
            <span className="text-text-muted">{row.label}</span>
            {isLoading ? (
              <div className="animate-pulse bg-gold/20 rounded h-5 w-20" />
            ) : (
              <span className={row.label === 'OLTIN' ? 'font-semibold text-gold' : 'font-semibold'}>
                {row.value}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          href="/send"
          onClick={() => hapticFeedback('medium')}
          className="bg-card rounded-xl p-4 flex items-center gap-3 border border-border hover:border-gold/50 transition-colors"
        >
          <div className="w-10 h-10 rounded-full bg-gold/20 flex items-center justify-center">
            <ArrowUpRight size={20} className="text-gold" />
          </div>
          <span className="font-medium">{t('send')}</span>
        </Link>
        <Link
          href="/receive"
          onClick={() => hapticFeedback('medium')}
          className="bg-card rounded-xl p-4 flex items-center gap-3 border border-border hover:border-green/50 transition-colors"
        >
          <div className="w-10 h-10 rounded-full bg-green/20 flex items-center justify-center">
            <ArrowDownLeft size={20} className="text-green" />
          </div>
          <span className="font-medium">{t('receive')}</span>
        </Link>
      </div>

      {/* Recent Transactions */}
      <div className="bg-card rounded-xl p-4 border border-border">
        <h3 className="font-semibold mb-3">{t('recentTransactions')}</h3>
        {!history.length ? (
          <p className="text-text-muted text-sm text-center py-4">{t('noTransactions')}</p>
        ) : (
          <div className="space-y-3">
            {history.slice(0, 8).map((tx) => {
              const positive = tx.kind === 'received' || tx.kind === 'minted';
              const negative = tx.kind === 'sent' || tx.kind === 'burned';
              return (
                <a
                  // A collapsed BUY/SELL yields two rows sharing one tx_hash
                  // (a UZD leg + an OLTIN leg), so the hash alone is not unique.
                  // Compose with symbol/kind/amount for a stable per-row key.
                  key={`${tx.tx_hash}-${tx.symbol}-${tx.kind}-${tx.amount_wei}`}
                  href={tx.explorer_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      positive ? 'bg-green/20' : negative ? 'bg-red/20' : 'bg-background'
                    }`}>
                      {negative ? (
                        <ArrowUpRight size={16} className="text-red" />
                      ) : (
                        <ArrowDownLeft size={16} className={positive ? 'text-green' : 'text-text-muted'} />
                      )}
                    </div>
                    <div>
                      <div className="text-sm font-medium">{kindLabel(tx.kind)}</div>
                      <div className="text-xs text-text-muted">
                        {new Date(tx.indexed_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  {tx.amount_wei && (
                    <div className={`font-semibold ${
                      positive ? 'text-green' : negative ? 'text-red' : 'text-text-muted'
                    }`}>
                      {positive ? '+' : negative ? '-' : ''}{formatToken(tx.amount_wei)} {tx.symbol}
                    </div>
                  )}
                </a>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
