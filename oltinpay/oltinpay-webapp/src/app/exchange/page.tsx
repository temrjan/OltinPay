'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatUnits } from 'viem';
import { AlertCircle, CheckCircle, ArrowDownUp, Info, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { useBalances } from '@/hooks/useBalances';
import { useRates } from '@/hooks/useRates';
import { api } from '@/lib/api';
import { CONTRACTS } from '@/lib/contracts';
import {
  approveForExchange,
  exchangeBuy,
  exchangeSell,
  publicClient,
} from '@/lib/chain';
import { formatToken, parseTokenAmount, computeMinOut } from '@/lib/format';
import { useWalletStore } from '@/stores/wallet';

const TOKEN_DECIMALS = 18;
const RECEIPT_TIMEOUT_MS = 60_000;
const SLIPPAGE_BPS = 100; // 1%

export default function ExchangePage() {
  const { hapticFeedback } = useTelegram();
  const { t, language } = useTranslation();
  const queryClient = useQueryClient();
  const account = useWalletStore((s) => s.account);

  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [amount, setAmount] = useState('');
  const [success, setSuccess] = useState(false);
  const [step, setStep] = useState<null | 'approving' | 'swapping'>(null);

  const L = (uz: string, ru: string, en: string) =>
    language === 'uz' ? uz : language === 'ru' ? ru : en;

  const { data: rates, isLoading: ratesLoading } = useRates();
  const { data: balancesData } = useBalances();

  const oltinPriceUzd = rates?.oltin_price_uzd ?? null;

  // Both UZD and OLTIN are 18-decimal; balances + amount are in wei (bigint).
  const uzdWei = balancesData ? BigInt(balancesData.wallet.uzd_wei) : BigInt(0);
  const oltinWei = balancesData ? BigInt(balancesData.wallet.oltin_wei) : BigInt(0);

  const amountWei = parseTokenAmount(amount, TOKEN_DECIMALS);
  const spendWei = side === 'buy' ? uzdWei : oltinWei;
  const spendSymbol = side === 'buy' ? 'UZD' : 'OLTIN';
  const receiveSymbol = side === 'buy' ? 'OLTIN' : 'UZD';
  const exceedsBalance = amountWei !== null && amountWei > spendWei;
  const amountValid = amountWei !== null && !exceedsBalance;

  // Quote (auth-gated — request() attaches the token). Only for a valid amount;
  // short refetch so the estimate stays close to what the swap executes at.
  const { data: quote, isFetching: quoteFetching } = useQuery({
    queryKey: ['quote', side, amount],
    queryFn: () => api.getQuote(side, amount.trim()),
    enabled: amountValid,
    refetchInterval: 10000,
  });
  const estimatedOut = quote?.estimated_out ?? null;

  // Map an on-chain error to a localized message. `afterApprove` adds the "approve
  // already spent" note (the two-step path can spend approve gas then revert buy).
  const explain = (raw: string, afterApprove: boolean): string => {
    if (/insufficient funds|exceeds the balance/i.test(raw)) {
      return L('Gaz uchun ETH yetarli emas', 'Недостаточно ETH на газ', 'Not enough ETH for gas');
    }
    if (/reserve stale|price stale/i.test(raw)) {
      const base = L('Narx eskirgan (keeper)', 'Цена устарела (keeper)', 'Price is stale (keeper)');
      return afterApprove
        ? base + L(' — approve sarflandi, keyinroq', ' — approve потрачен, позже', ' — approve spent, try later')
        : base;
    }
    if (/treasury empty/i.test(raw)) {
      return L('Birja hozir tolay olmaydi', 'Биржа временно не может выкупить', 'Exchange cannot pay out now');
    }
    if (/dust/i.test(raw)) {
      return L('Summa juda kichik', 'Сумма слишком мала', 'Amount too small');
    }
    if (/slippage/i.test(raw)) {
      return L('Narx ozgardi, qayta urining', 'Цена изменилась, попробуйте снова', 'Price moved, try again');
    }
    return afterApprove
      ? L('Almashuv rad etildi (approve sarflandi)', 'Обмен отклонён (approve потрачен)', 'Swap reverted (approve spent)')
      : L('Tranzaksiya yuborilmadi', 'Транзакция не отправлена', 'Transaction failed');
  };

  const swapMutation = useMutation({
    mutationFn: async () => {
      if (!account) throw new Error(L('Hamyon qulflangan', 'Кошелёк заблокирован', 'Wallet is locked'));
      if (amountWei === null) throw new Error(L('Notogri summa', 'Неверная сумма', 'Invalid amount'));
      if (amountWei > spendWei) {
        throw new Error(L('Balans yetarli emas', 'Недостаточно средств', 'Insufficient balance'));
      }
      // Fresh quote right before signing (not the 10s cache) + verify it matches
      // the side we're signing for — defense-in-depth on the money path (Gate-2).
      const freshQuote = await api.getQuote(side, amount.trim()).catch(() => null);
      if (!freshQuote) {
        throw new Error(L('Narx hozir mavjud emas', 'Цена сейчас недоступна', 'Price unavailable right now'));
      }
      if (freshQuote.side !== side || !freshQuote.estimated_out_wei) {
        throw new Error(L('Kotirovka mos emas, qayta urining', 'Котировка не совпала, попробуйте снова', 'Quote mismatch, try again'));
      }
      const minOut = computeMinOut(freshQuote.estimated_out_wei, SLIPPAGE_BPS);
      if (minOut === null) {
        throw new Error(L('Summa juda kichik', 'Сумма слишком мала', 'Amount too small'));
      }
      const token = side === 'buy' ? CONTRACTS.UZD : CONTRACTS.OLTIN;

      // Step 1 — approve the Exchange to move the input token.
      setStep('approving');
      let approveHash: `0x${string}`;
      try {
        approveHash = await approveForExchange(account, token, amountWei);
      } catch (err) {
        throw new Error(explain(err instanceof Error ? err.message : String(err), false));
      }
      const approveReceipt = await publicClient.waitForTransactionReceipt({
        hash: approveHash,
        timeout: RECEIPT_TIMEOUT_MS,
      });
      if (approveReceipt.status !== 'success') {
        throw new Error(L('Approve rad etildi', 'Approve отклонён', 'Approve reverted'));
      }

      // Step 2 — buy/sell. From here, an error means approve gas was already spent.
      setStep('swapping');
      let swapHash: `0x${string}`;
      try {
        swapHash =
          side === 'buy'
            ? await exchangeBuy(account, amountWei, minOut)
            : await exchangeSell(account, amountWei, minOut);
      } catch (err) {
        throw new Error(explain(err instanceof Error ? err.message : String(err), true));
      }
      const swapReceipt = await publicClient.waitForTransactionReceipt({
        hash: swapHash,
        timeout: RECEIPT_TIMEOUT_MS,
      });
      if (swapReceipt.status !== 'success') {
        throw new Error(explain('reverted', true));
      }
      return swapHash;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['balances'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setAmount('');
      setSuccess(true);
      hapticFeedback('success');
      setTimeout(() => setSuccess(false), 3000);
    },
    onError: () => hapticFeedback('error'),
    onSettled: () => setStep(null),
  });

  const canSwap = amountValid && !!quote?.estimated_out_wei && !swapMutation.isPending;
  const walletUzd = balancesData ? formatToken(balancesData.wallet.uzd_wei) : '0';
  const walletOltin = balancesData ? formatToken(balancesData.wallet.oltin_wei) : '0';

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">{t('exchange')}</h1>

      {/* Wallet balance */}
      <div className="bg-card rounded-xl p-4 border border-border">
        <div className="flex justify-between items-center mb-2">
          <span className="text-text-muted text-sm">
            {L('Hamyon', 'Кошелёк', 'Wallet')}
          </span>
          <Link href="/send" className="text-gold text-xs">
            {L("Pul o'tkazish →", 'Перевести →', 'Transfer →')}
          </Link>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-2xl font-bold">{walletUzd}</div>
            <div className="text-text-muted text-xs">UZD</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-gold">{walletOltin}</div>
            <div className="text-text-muted text-xs">OLTIN</div>
          </div>
        </div>
      </div>

      {/* Real on-chain price (UZS per OLTIN) */}
      <div className="bg-gold/10 border-2 border-gold rounded-xl p-4 text-center">
        <div className="text-text-muted text-sm">
          {L('OLTIN narxi', 'Цена OLTIN', 'OLTIN price')}
        </div>
        {ratesLoading || oltinPriceUzd === null ? (
          <div className="h-9 flex items-center justify-center">
            <div className="animate-pulse bg-gold/20 rounded h-8 w-40" />
          </div>
        ) : (
          <div className="text-2xl font-bold text-gold">
            {oltinPriceUzd.toLocaleString('en-US', { maximumFractionDigits: 0 })}{' '}
            <span className="text-lg">UZD</span>
          </div>
        )}
        <div className="text-text-muted text-xs">1 OLTIN = 1g {L('oltin', 'золота', 'gold')}</div>
      </div>

      {/* Success / error */}
      {success && (
        <div className="bg-green/10 border border-green rounded-xl p-3 flex items-center gap-2">
          <CheckCircle size={20} className="text-green" />
          <span className="text-green text-sm">
            {L('Muvaffaqiyatli almashildi!', 'Обмен выполнен!', 'Swap successful!')}
          </span>
        </div>
      )}
      {swapMutation.isError && (
        <div className="bg-red/10 border border-red rounded-xl p-3 flex items-center gap-2">
          <AlertCircle size={20} className="text-red" />
          <span className="text-red text-sm">{(swapMutation.error as Error)?.message}</span>
        </div>
      )}

      {/* Buy / Sell toggle */}
      <div className="flex bg-card rounded-xl p-1 border border-border">
        <button
          onClick={() => { setSide('buy'); setAmount(''); hapticFeedback('selection'); }}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'buy' ? 'bg-gold text-background' : 'text-text-muted'
          }`}
        >
          {L('Sotib olish', 'Купить', 'Buy')}
        </button>
        <button
          onClick={() => { setSide('sell'); setAmount(''); hapticFeedback('selection'); }}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'sell' ? 'bg-gold text-background' : 'text-text-muted'
          }`}
        >
          {L('Sotish', 'Продать', 'Sell')}
        </button>
      </div>

      {/* You pay */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-text-muted text-sm">{L('Tolaysiz', 'Отдаёте', 'You pay')}</span>
          <button
            onClick={() => setAmount(formatUnits(spendWei, TOKEN_DECIMALS))}
            className="text-gold text-sm"
          >
            {L('Bor', 'Доступно', 'Available')}: {formatToken(spendWei.toString())} {spendSymbol}
          </button>
        </div>
        <div className="flex items-center gap-2 bg-background border border-border rounded-xl px-4 py-3">
          <input
            type="number"
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            className="flex-1 bg-transparent text-xl focus:outline-none"
          />
          <span className="text-text-muted font-medium">{spendSymbol}</span>
        </div>
        {exceedsBalance && (
          <div className="text-red text-sm">{L('Balansdan oshib ketdi', 'Больше баланса', 'Exceeds balance')}</div>
        )}
      </div>

      {/* Arrow */}
      <div className="flex justify-center">
        <div className="p-2 rounded-full bg-background border border-border">
          <ArrowDownUp size={20} className="text-gold" />
        </div>
      </div>

      {/* You receive */}
      <div className="space-y-2">
        <div className="text-text-muted text-sm">{L('Olasiz', 'Получаете', 'You receive')}</div>
        <div className="flex items-center gap-2 bg-background border border-border rounded-xl px-4 py-3">
          <div className="flex-1 text-xl">
            {!amountValid ? (
              <span className="text-text-muted">0.00</span>
            ) : quoteFetching && estimatedOut === null ? (
              <span className="text-text-muted">…</span>
            ) : estimatedOut !== null ? (
              <span>{estimatedOut.toLocaleString('en-US', { maximumFractionDigits: 4 })}</span>
            ) : (
              <span className="text-text-muted">0.00</span>
            )}
          </div>
          <span className="text-text-muted font-medium">{receiveSymbol}</span>
        </div>
        <div className="text-text-muted text-xs">
          {L('Komissiyasiz — 1% slippage himoyasi; gaz ETH da', 'Без комиссии — защита 1% slippage; газ в ETH', 'No fee — 1% slippage guard; gas in ETH')}
        </div>
      </div>

      {/* Swap button */}
      <button
        onClick={() => swapMutation.mutate()}
        disabled={!canSwap}
        className="w-full py-4 rounded-xl font-semibold transition-colors disabled:opacity-50 bg-gold text-background flex items-center justify-center gap-2"
      >
        {swapMutation.isPending ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            {step === 'approving'
              ? L('Ruxsat berilmoqda…', 'Разрешение…', 'Approving…')
              : L('Almashilmoqda…', 'Обмен…', 'Swapping…')}
          </>
        ) : side === 'buy' ? (
          L('Sotib olish', 'Купить', 'Buy')
        ) : (
          L('Sotish', 'Продать', 'Sell')
        )}
      </button>

      {/* Info */}
      <div className="bg-card rounded-xl p-3 flex items-start gap-2 border border-border">
        <Info size={16} className="text-text-muted shrink-0 mt-0.5" />
        <span className="text-text-muted text-xs">
          {L(
            'Narx jonli fiddan (XAU/UZS). Sotib olish → OLTIN zarb qilinadi; sotish → OLTIN yoqiladi.',
            'Цена из живого фида (XAU/UZS). Покупка чеканит OLTIN; продажа сжигает OLTIN.',
            'Price from the live feed (XAU/UZS). Buy mints OLTIN; sell burns OLTIN.',
          )}
        </span>
      </div>
    </div>
  );
}
