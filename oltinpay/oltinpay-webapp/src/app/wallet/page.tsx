'use client';

import { useState } from 'react';
import { ArrowUpRight, ArrowDownLeft, RefreshCw, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { api } from '@/lib/api';
import { useAppStore } from '@/stores/app';

type AccountType = 'wallet' | 'exchange' | 'staking';

interface AccountBalance {
  usd: number;
  oltin: number;
}

interface BalancesResponse {
  total_usd: number;
  wallet: AccountBalance;
  exchange: AccountBalance;
  staking: AccountBalance;
}

export default function WalletPage() {
  const { user: tgUser, hapticFeedback } = useTelegram();
  const { t } = useTranslation();
  const user = useAppStore((state) => state.user);
  const [activeTab, setActiveTab] = useState<AccountType>('wallet');

  const { data: balancesData, isLoading, error, refetch } = useQuery({
    queryKey: ['balances'],
    queryFn: () => api.getBalances() as Promise<BalancesResponse>,
    staleTime: 30000,
  });

  const { data: transfersData } = useQuery({
    queryKey: ['transfers'],
    queryFn: () => api.getTransfers(5),
    staleTime: 30000,
  });

  const getBalance = (account: AccountType, currency: 'usd' | 'oltin'): number => {
    if (!balancesData) return 0;
    const accountData = balancesData[account];
    if (!accountData) return 0;
    return Number(accountData[currency]) || 0;
  };

  const tabs = [
    { id: 'wallet', label: t('wallet') },
    { id: 'exchange', label: t('exchange') },
    { id: 'staking', label: t('staking') },
  ] as const;

  const displayName = user?.oltin_id?.startsWith('user_')
    ? tgUser?.first_name || 'User'
    : `@${user?.oltin_id}`;

  const totalUsd = balancesData?.total_usd || 0;
  const currentUsd = getBalance(activeTab, 'usd');
  const currentOltin = getBalance(activeTab, 'oltin');

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
          <div className="text-3xl font-bold text-gold">${ Number(totalUsd).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        )}
        <div className="text-text-muted text-sm mt-1">{t('totalBalance')}</div>
      </div>

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
        <div className="flex justify-between items-center">
          <span className="text-text-muted">USD</span>
          {isLoading ? (
            <div className="animate-pulse bg-gold/20 rounded h-5 w-20" />
          ) : (
            <span className="font-semibold">${currentUsd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          )}
        </div>
        <div className="flex justify-between items-center">
          <span className="text-text-muted">OLTIN</span>
          {isLoading ? (
            <div className="animate-pulse bg-gold/20 rounded h-5 w-20" />
          ) : (
            <span className="font-semibold text-gold">{currentOltin.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</span>
          )}
        </div>
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
        {!transfersData?.length ? (
          <p className="text-text-muted text-sm text-center py-4">{t('noTransactions')}</p>
        ) : (
          <div className="space-y-3">
            {transfersData.slice(0, 5).map((tx: any) => (
              <div key={tx.id} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    tx.type === 'incoming' ? 'bg-green/20' : 'bg-red/20'
                  }`}>
                    {tx.type === 'incoming' ? (
                      <ArrowDownLeft size={16} className="text-green" />
                    ) : (
                      <ArrowUpRight size={16} className="text-red" />
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-medium">
                      {tx.type === 'incoming' ? t('received') : t('sent')}
                    </div>
                    <div className="text-xs text-text-muted">
                      {new Date(tx.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <div className={`font-semibold ${
                  tx.type === 'incoming' ? 'text-green' : 'text-red'
                }`}>
                  {tx.type === 'incoming' ? '+' : '-'}{tx.amount} {tx.currency}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
