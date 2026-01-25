'use client';

import { useState } from 'react';
import { ArrowUpRight, ArrowDownLeft, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';

export default function WalletPage() {
  const { user, hapticFeedback } = useTelegram();
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'wallet' | 'exchange' | 'staking'>('wallet');

  const balances = {
    wallet: { usd: 1000.00, oltin: 0 },
    exchange: { usd: 0, oltin: 0 },
    staking: { usd: 0, oltin: 0 },
  };

  const tabs = [
    { id: 'wallet', label: t('wallet') },
    { id: 'exchange', label: t('exchange') },
    { id: 'staking', label: t('staking') },
  ] as const;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-text-muted text-sm">{t('hello')},</div>
          <div className="text-xl font-semibold">{user?.first_name || 'User'}</div>
        </div>
        <button onClick={() => hapticFeedback('light')} className="p-2 rounded-full hover:bg-card">
          <RefreshCw size={20} className="text-text-muted" />
        </button>
      </div>

      <div className="flex bg-card rounded-xl p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); hapticFeedback('selection'); }}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-semibold transition-colors ${
              activeTab === tab.id ? 'bg-gold text-background' : 'text-text-muted'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="bg-card rounded-xl p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-text-muted text-xs mb-1">USD</div>
            <div className="text-2xl font-bold">${balances[activeTab].usd.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-text-muted text-xs mb-1">OLTIN</div>
            <div className="text-2xl font-bold text-gold">{balances[activeTab].oltin.toFixed(4)}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Link href="/send" onClick={() => hapticFeedback('medium')} className="bg-card rounded-xl p-4 flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-full bg-gold/20 flex items-center justify-center">
            <ArrowUpRight className="text-gold" size={24} />
          </div>
          <span className="text-sm font-semibold">{t('send')}</span>
        </Link>
        <Link href="/receive" onClick={() => hapticFeedback('medium')} className="bg-card rounded-xl p-4 flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-full bg-green/20 flex items-center justify-center">
            <ArrowDownLeft className="text-green" size={24} />
          </div>
          <span className="text-sm font-semibold">{t('receive')}</span>
        </Link>
      </div>

      <div className="bg-card rounded-xl p-4">
        <h3 className="font-semibold mb-3">{t('recentTransactions')}</h3>
        <div className="text-center text-text-muted py-4">{t('noTransactions')}</div>
      </div>
    </div>
  );
}
