'use client';

import { useState } from 'react';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';

export default function ExchangePage() {
  const { hapticFeedback } = useTelegram();
  const { t } = useTranslation();
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [amount, setAmount] = useState('');

  const goldPrice = 2650.50;

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">{t('exchange')}</h1>

      <div className="bg-card rounded-xl p-4 text-center">
        <div className="text-text-muted text-sm">{t('goldPrice')}</div>
        <div className="text-3xl font-bold text-gold">${goldPrice.toFixed(2)}</div>
        <div className="text-text-muted text-xs">1 OLTIN = 1g gold</div>
      </div>

      <div className="flex bg-card rounded-xl p-1">
        <button
          onClick={() => { setSide('buy'); hapticFeedback('selection'); }}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'buy' ? 'bg-green text-background' : 'text-text-muted'
          }`}
        >
          {t('buy')}
        </button>
        <button
          onClick={() => { setSide('sell'); hapticFeedback('selection'); }}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'sell' ? 'bg-red text-background' : 'text-text-muted'
          }`}
        >
          {t('sell')}
        </button>
      </div>

      <div className="bg-card rounded-xl p-4 space-y-3">
        <label className="text-text-muted text-sm">{t('amount')} (USD)</label>
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.00"
          className="w-full bg-background border border-border rounded-xl px-4 py-3 text-xl focus:outline-none focus:border-gold"
        />
        {amount && (
          <div className="text-text-muted text-sm">
            ≈ {(parseFloat(amount) / goldPrice).toFixed(6)} OLTIN
          </div>
        )}
      </div>

      <button
        onClick={() => hapticFeedback('medium')}
        disabled={!amount}
        className={`w-full py-4 rounded-xl font-semibold transition-colors ${
          side === 'buy' ? 'bg-green text-background disabled:opacity-50' : 'bg-red text-background disabled:opacity-50'
        }`}
      >
        {side === 'buy' ? t('buy') : t('sell')}
      </button>
    </div>
  );
}
