'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { api } from '@/lib/api';
import { AlertCircle, CheckCircle, ArrowDownUp, Info } from 'lucide-react';
import Link from 'next/link';

export default function ExchangePage() {
  const { hapticFeedback } = useTelegram();
  const { t, language } = useTranslation();
  const queryClient = useQueryClient();

  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [amount, setAmount] = useState('');
  const [success, setSuccess] = useState(false);

  // Get price
  const { data: priceData, isLoading: priceLoading } = useQuery({
    queryKey: ['price'],
    queryFn: () => api.getPrice(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Get balances
  const { data: balancesData } = useQuery({
    queryKey: ['balances'],
    queryFn: () => api.getBalances(),
  });

  // Get swap quote
  const { data: quoteData, isLoading: quoteLoading } = useQuery({
    queryKey: ['swapQuote', side, amount],
    queryFn: () => api.getSwapQuote({
      side,
      amount: parseFloat(amount),
      amount_type: 'from',
    }),
    enabled: !!amount && parseFloat(amount) > 0,
    refetchInterval: 10000,
  });

  // Execute swap mutation
  const swapMutation = useMutation({
    mutationFn: () => api.executeSwap({
      side,
      amount: parseFloat(amount),
      amount_type: 'from',
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['balances'] });
      setAmount('');
      setSuccess(true);
      hapticFeedback('success');
      setTimeout(() => setSuccess(false), 3000);
    },
    onError: () => {
      hapticFeedback('error');
    },
  });

  // Get exchange account balances
  const exchangeUsd = balancesData?.exchange?.usd ? Number(balancesData.exchange.usd) : 0;
  const exchangeOltin = balancesData?.exchange?.oltin ? Number(balancesData.exchange.oltin) : 0;

  // Price display
  const midPrice = priceData?.mid ? Number(priceData.mid) : 85;
  const bidPrice = priceData?.bid ? Number(priceData.bid) : 84.5;
  const askPrice = priceData?.ask ? Number(priceData.ask) : 85.5;
  const currentPrice = side === 'buy' ? askPrice : bidPrice;

  // Available balance for current operation
  const availableBalance = side === 'buy' ? exchangeUsd : exchangeOltin;
  const balanceCurrency = side === 'buy' ? 'USD' : 'OLTIN';

  // Check if can swap
  const canSwap = amount &&
    parseFloat(amount) > 0 &&
    parseFloat(amount) <= availableBalance &&
    !swapMutation.isPending;

  const handleSwap = () => {
    if (!canSwap) return;
    swapMutation.mutate();
  };

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">{t('exchange')}</h1>

      {/* Exchange Account Balance */}
      <div className="bg-card rounded-xl p-4 border border-border">
        <div className="flex justify-between items-center mb-2">
          <span className="text-text-muted text-sm">
            {language === 'uz' ? 'Birja hisobi' : language === 'ru' ? 'Счёт биржи' : 'Exchange Account'}
          </span>
          <Link href="/send" className="text-gold text-xs">
            {language === 'uz' ? "Pul o'tkazish →" : language === 'ru' ? 'Пополнить →' : 'Transfer →'}
          </Link>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-2xl font-bold">${exchangeUsd.toFixed(2)}</div>
            <div className="text-text-muted text-xs">USD</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-gold">{exchangeOltin.toFixed(4)}</div>
            <div className="text-text-muted text-xs">OLTIN</div>
          </div>
        </div>
      </div>

      {/* Price display */}
      <div className="bg-gold/10 border-2 border-gold rounded-xl p-4 text-center">
        <div className="text-text-muted text-sm">{t('goldPrice')}</div>
        {priceLoading ? (
          <div className="h-9 flex items-center justify-center">
            <div className="animate-pulse bg-gold/20 rounded h-8 w-32" />
          </div>
        ) : (
          <div className="text-3xl font-bold text-gold">${midPrice.toFixed(2)}</div>
        )}
        <div className="text-text-muted text-xs">1 OLTIN = 1g gold</div>

        {/* Bid/Ask spread */}
        <div className="flex justify-center gap-4 mt-2 text-sm">
          <span className="text-green">
            {language === 'uz' ? 'Sotish' : language === 'ru' ? 'Продажа' : 'Sell'}: ${bidPrice.toFixed(2)}
          </span>
          <span className="text-red">
            {language === 'uz' ? 'Sotib olish' : language === 'ru' ? 'Покупка' : 'Buy'}: ${askPrice.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Success message */}
      {success && (
        <div className="bg-green/10 border border-green rounded-xl p-3 flex items-center gap-2">
          <CheckCircle size={20} className="text-green" />
          <span className="text-green text-sm">
            {language === 'uz' ? 'Muvaffaqiyatli almashildi!' : language === 'ru' ? 'Обмен выполнен!' : 'Swap successful!'}
          </span>
        </div>
      )}

      {/* Error message */}
      {swapMutation.isError && (
        <div className="bg-red/10 border border-red rounded-xl p-3 flex items-center gap-2">
          <AlertCircle size={20} className="text-red" />
          <span className="text-red text-sm">{(swapMutation.error as Error)?.message}</span>
        </div>
      )}

      {/* Buy/Sell toggle */}
      <div className="flex bg-card rounded-xl p-1 border border-border">
        <button
          onClick={() => { setSide('buy'); setAmount(''); hapticFeedback('selection'); }}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'buy' ? 'bg-green text-background' : 'text-text-muted'
          }`}
        >
          {t('buy')} OLTIN
        </button>
        <button
          onClick={() => { setSide('sell'); setAmount(''); hapticFeedback('selection'); }}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'sell' ? 'bg-red text-background' : 'text-text-muted'
          }`}
        >
          {t('sell')} OLTIN
        </button>
      </div>

      {/* Swap form */}
      <div className="bg-card rounded-xl p-4 space-y-4 border border-border">
        {/* From */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="text-text-muted">
              {language === 'uz' ? 'Beraman' : language === 'ru' ? 'Отдаю' : 'You pay'}
            </span>
            <button
              onClick={() => setAmount(availableBalance.toString())}
              className="text-gold"
            >
              {t('available')}: {availableBalance.toFixed(side === 'buy' ? 2 : 4)} {balanceCurrency}
            </button>
          </div>
          <div className="flex items-center gap-2 bg-background border border-border rounded-xl px-4 py-3">
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              className="flex-1 bg-transparent text-xl focus:outline-none"
            />
            <span className="text-text-muted font-medium">{balanceCurrency}</span>
          </div>
        </div>

        {/* Arrow */}
        <div className="flex justify-center">
          <div className="p-2 rounded-full bg-background border border-border">
            <ArrowDownUp size={20} className="text-gold" />
          </div>
        </div>

        {/* To */}
        <div>
          <div className="text-text-muted text-sm mb-2">
            {language === 'uz' ? 'Olaman' : language === 'ru' ? 'Получу' : 'You receive'}
          </div>
          <div className="flex items-center gap-2 bg-background border border-border rounded-xl px-4 py-3">
            <div className="flex-1 text-xl">
              {quoteLoading ? (
                <span className="text-text-muted">...</span>
              ) : quoteData ? (
                <span>{Number(quoteData.to_amount).toFixed(side === 'buy' ? 4 : 2)}</span>
              ) : (
                <span className="text-text-muted">0.00</span>
              )}
            </div>
            <span className="text-text-muted font-medium">{side === 'buy' ? 'OLTIN' : 'USD'}</span>
          </div>
        </div>

        {/* Quote details */}
        {quoteData && amount && (
          <div className="text-sm text-text-muted space-y-1">
            <div className="flex justify-between">
              <span>{language === 'uz' ? 'Kurs' : language === 'ru' ? 'Курс' : 'Rate'}:</span>
              <span>1 OLTIN = ${Number(quoteData.price).toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>{t('fee')} ({quoteData.fee_percent}%):</span>
              <span>{Number(quoteData.fee).toFixed(side === 'buy' ? 4 : 2)} {side === 'buy' ? 'OLTIN' : 'USD'}</span>
            </div>
          </div>
        )}
      </div>

      {/* Swap button */}
      <button
        onClick={handleSwap}
        disabled={!canSwap}
        className={`w-full py-4 rounded-xl font-semibold transition-colors disabled:opacity-50 ${
          side === 'buy' ? 'bg-green text-background' : 'bg-red text-background'
        }`}
      >
        {swapMutation.isPending ? '...' :
         side === 'buy'
           ? (language === 'uz' ? 'Sotib olish' : language === 'ru' ? 'Купить' : 'Buy')
           : (language === 'uz' ? 'Sotish' : language === 'ru' ? 'Продать' : 'Sell')
        }
      </button>

      {/* Info */}
      {exchangeUsd === 0 && exchangeOltin === 0 && (
        <div className="bg-card rounded-xl p-4 flex gap-3 border border-border">
          <Info size={20} className="text-gold flex-shrink-0 mt-0.5" />
          <div className="text-sm text-text-muted">
            {language === 'uz'
              ? "Almashtirish uchun avval Hamyondan Birja hisobiga pul o'tkazing."
              : language === 'ru'
              ? 'Для обмена сначала переведите средства из Кошелька на счёт Биржи.'
              : 'To swap, first transfer funds from Wallet to Exchange account.'
            }
            <Link href="/send" className="text-gold ml-1">
              {language === 'uz' ? "O'tkazish →" : language === 'ru' ? 'Перевести →' : 'Transfer →'}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
