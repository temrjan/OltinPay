'use client';

import { useState } from 'react';
import { ArrowLeft, Search, User, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatUnits } from 'viem';
import type { Address } from 'viem';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { useBalances } from '@/hooks/useBalances';
import { api } from '@/lib/api';
import { transferOltin, publicClient } from '@/lib/chain';
import { formatToken, parseTokenAmount } from '@/lib/format';
import { useAppStore } from '@/stores/app';
import { useWalletStore } from '@/stores/wallet';

interface UserSearchResult {
  id: string;
  oltin_id: string;
  telegram_id: number;
}

const OLTIN_DECIMALS = 18;
const RECEIPT_TIMEOUT_MS = 60_000;

export default function SendPage() {
  const { hapticFeedback } = useTelegram();
  const { t, language } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAppStore((state) => state.user);
  // The unlocked HD signer. The global WalletGate renders PinUnlock app-wide when
  // the wallet is locked, so this is non-null while the page shows — we still
  // guard it before signing (an idle session can expire mid-flow).
  const account = useWalletStore((s) => s.account);

  const [step, setStep] = useState<'recipient' | 'amount' | 'confirm' | 'success'>('recipient');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRecipient, setSelectedRecipient] = useState<UserSearchResult | null>(null);
  // Raw input string — parsed to wei with parseUnits, never via parseFloat (an
  // 18-decimal amount does not survive a JS float round-trip).
  const [amount, setAmount] = useState('');

  // Inline localizer — matches the existing per-string pattern in this app.
  const L = (uz: string, ru: string, en: string) =>
    language === 'uz' ? uz : language === 'ru' ? ru : en;

  const { data: balancesData } = useBalances();

  // Wallet OLTIN balance in wei (bigint) — the source of truth for the send.
  const oltinWei = balancesData ? BigInt(balancesData.wallet.oltin_wei) : BigInt(0);

  // Parse the raw amount to wei; null when empty/invalid (e.g. "abc", "0", "-1").
  const amountWei = parseTokenAmount(amount, OLTIN_DECIMALS);
  const exceedsBalance = amountWei !== null && amountWei > oltinWei;
  const amountValid = amountWei !== null && !exceedsBalance;

  const isSelf = Boolean(
    user?.oltin_id &&
      selectedRecipient?.oltin_id &&
      selectedRecipient.oltin_id.toLowerCase() === user.oltin_id.toLowerCase(),
  );

  // Search / contacts
  const { data: searchResults, isLoading: searching } = useQuery({
    queryKey: ['searchUsers', searchQuery],
    queryFn: () => api.searchUsers(searchQuery),
    enabled: searchQuery.length >= 2,
  });
  const { data: recentContacts } = useQuery({
    queryKey: ['recentContacts'],
    queryFn: () => api.getRecentContacts(),
  });
  const { data: favorites } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => api.getFavorites(),
  });

  // Resolve the recipient's on-chain address once selected (privacy: a single
  // targeted lookup, not exposed in search). Drives the confirm screen + the send.
  const { data: recipientLookup, isLoading: resolving } = useQuery({
    queryKey: ['userLookup', selectedRecipient?.oltin_id],
    queryFn: () => api.lookupUser(selectedRecipient!.oltin_id),
    enabled: !!selectedRecipient,
  });
  const recipientAddress = recipientLookup?.wallet_address ?? null;

  // Real on-chain P2P transfer: OLTIN.transfer signed by the user's wallet, then
  // WAIT for receipt.status === 'success' — a broadcast hash alone can still revert.
  const transferMutation = useMutation({
    mutationFn: async () => {
      if (!account) throw new Error(L('Hamyon qulflangan', 'Кошелёк заблокирован', 'Wallet is locked'));
      if (amountWei === null) throw new Error(L('Notogri summa', 'Неверная сумма', 'Invalid amount'));
      if (amountWei > oltinWei) {
        throw new Error(L('Balans yetarli emas', 'Недостаточно средств', 'Insufficient balance'));
      }
      if (isSelf) {
        throw new Error(L("O'zingizga yubora olmaysiz", 'Нельзя отправить самому себе', 'Cannot send to yourself'));
      }
      if (!recipientAddress) {
        throw new Error(
          L('Qabul qiluvchida hamyon yoq', 'У получателя ещё нет кошелька', 'Recipient has no wallet yet'),
        );
      }
      const to = recipientAddress as Address;
      // Backstop self-guard by resolved address (favorites/recent skip the search self-filter).
      if (balancesData && to.toLowerCase() === balancesData.wallet_address.toLowerCase()) {
        throw new Error(L("O'zingizga yubora olmaysiz", 'Нельзя отправить самому себе', 'Cannot send to yourself'));
      }
      let hash: `0x${string}`;
      try {
        hash = await transferOltin(account, to, amountWei);
      } catch (err) {
        const raw = err instanceof Error ? err.message : String(err);
        if (/insufficient funds|exceeds the balance|gas/i.test(raw)) {
          throw new Error(
            L(
              'Gaz uchun ETH yetarli emas',
              'Недостаточно ETH на газ',
              'Not enough ETH for gas',
            ),
          );
        }
        throw new Error(L('Tranzaksiya yuborilmadi', 'Транзакция не отправлена', 'Transaction failed'));
      }
      const receipt = await publicClient.waitForTransactionReceipt({
        hash,
        timeout: RECEIPT_TIMEOUT_MS,
      });
      if (receipt.status !== 'success') {
        throw new Error(L('Tranzaksiya rad etildi', 'Транзакция отклонена', 'Transaction reverted'));
      }
      return hash;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['balances'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['recentContacts'] });
      setStep('success');
      hapticFeedback('success');
    },
    onError: () => hapticFeedback('error'),
  });

  const handleSelectRecipient = (recipient: UserSearchResult) => {
    setSelectedRecipient(recipient);
    setAmount('');
    setStep('amount');
    hapticFeedback('selection');
  };

  const reset = () => {
    setStep('recipient');
    setSearchQuery('');
    setSelectedRecipient(null);
    setAmount('');
    transferMutation.reset();
  };

  const truncate = (addr: string) => `${addr.slice(0, 6)}…${addr.slice(-4)}`;
  const availableDisplay = balancesData ? formatToken(balancesData.wallet.oltin_wei) : '0';
  const canConfirm =
    !transferMutation.isPending && !resolving && !!recipientAddress && !isSelf && amountValid;

  return (
    <div className="flex flex-col min-h-[calc(100vh-60px)]">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-border">
        {step === 'success' ? (
          <button onClick={reset} className="text-text-muted">
            <ArrowLeft size={24} />
          </button>
        ) : step === 'recipient' ? (
          <Link href="/wallet" className="text-text-muted">
            <ArrowLeft size={24} />
          </Link>
        ) : (
          <button
            onClick={() => setStep(step === 'confirm' ? 'amount' : 'recipient')}
            className="text-text-muted"
          >
            <ArrowLeft size={24} />
          </button>
        )}
        <h1 className="text-lg font-semibold">{t('send')}</h1>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-4">
        {/* Success */}
        {step === 'success' && (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="w-20 h-20 rounded-full bg-green/20 flex items-center justify-center">
              <CheckCircle size={40} className="text-green" />
            </div>
            <div className="text-xl font-semibold">{t('transferSuccess')}</div>
            <div className="text-text-muted text-center">
              {amount} OLTIN → @{selectedRecipient?.oltin_id}
            </div>
            <Link href="/wallet" className="bg-gold text-background px-6 py-3 rounded-xl font-semibold">
              {t('backToWallet')}
            </Link>
          </div>
        )}

        {/* Recipient */}
        {step === 'recipient' && (
          <>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted" size={20} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value.replace('@', ''))}
                placeholder={t('searchPlaceholder')}
                className="w-full bg-card border border-border rounded-xl pl-12 pr-4 py-3 focus:outline-none focus:border-gold"
              />
            </div>

            {searching && (
              <div className="flex justify-center py-4">
                <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-gold" />
              </div>
            )}

            {searchResults && searchResults.length > 0 && (
              <div className="space-y-2">
                {searchResults
                  .filter((u: UserSearchResult) => u.id !== user?.id)
                  .map((u: UserSearchResult) => (
                    <button
                      key={u.id}
                      onClick={() => handleSelectRecipient(u)}
                      className="w-full bg-card border border-border rounded-xl p-4 flex items-center gap-3 hover:border-gold transition-colors"
                    >
                      <div className="w-10 h-10 rounded-full bg-gold/20 flex items-center justify-center">
                        <User className="text-gold" size={20} />
                      </div>
                      <span>@{u.oltin_id}</span>
                    </button>
                  ))}
              </div>
            )}

            {!searchQuery && favorites && favorites.length > 0 && (
              <div>
                <h3 className="text-text-muted text-sm mb-2">{t('favorites')}</h3>
                <div className="space-y-2">
                  {favorites.map((f: any) => (
                    <button
                      key={f.id}
                      onClick={() =>
                        handleSelectRecipient({
                          id: f.contact_user_id,
                          oltin_id: f.contact_oltin_id,
                          telegram_id: 0,
                        })
                      }
                      className="w-full bg-card border border-border rounded-xl p-4 flex items-center gap-3 hover:border-gold transition-colors"
                    >
                      <div className="w-10 h-10 rounded-full bg-gold/20 flex items-center justify-center">
                        <User className="text-gold" size={20} />
                      </div>
                      <span>@{f.contact_oltin_id}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {!searchQuery && recentContacts && recentContacts.length > 0 && (
              <div>
                <h3 className="text-text-muted text-sm mb-2">{t('recent')}</h3>
                <div className="space-y-2">
                  {recentContacts.slice(0, 5).map((c: any) => (
                    <button
                      key={c.user_id}
                      onClick={() =>
                        handleSelectRecipient({ id: c.user_id, oltin_id: c.oltin_id, telegram_id: 0 })
                      }
                      className="w-full bg-card border border-border rounded-xl p-4 flex items-center gap-3 hover:border-gold transition-colors"
                    >
                      <div className="w-10 h-10 rounded-full bg-card flex items-center justify-center">
                        <User className="text-text-muted" size={20} />
                      </div>
                      <span>@{c.oltin_id}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Amount */}
        {step === 'amount' && (
          <>
            <div className="text-center text-text-muted text-sm mb-2">
              {t('to')}: @{selectedRecipient?.oltin_id}
            </div>
            <input
              type="number"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.0000"
              className="w-full bg-background border border-border rounded-xl px-4 py-3 text-2xl text-center focus:outline-none focus:border-gold"
            />
            <div className="text-center">
              {/* Max sets the exact wei balance as a string — parseUnits round-trips it. */}
              <button
                onClick={() => setAmount(formatUnits(oltinWei, OLTIN_DECIMALS))}
                className="text-gold text-sm"
              >
                {t('available')}: {availableDisplay} OLTIN
              </button>
            </div>
            {exceedsBalance && (
              <div className="text-red text-sm text-center">
                {L('Balansdan oshib ketdi', 'Больше баланса', 'Exceeds balance')}
              </div>
            )}
            <button
              onClick={() => {
                setStep('confirm');
                hapticFeedback('medium');
              }}
              disabled={!amountValid}
              className="w-full bg-gold text-background py-4 rounded-xl font-semibold disabled:opacity-50"
            >
              {t('continue')}
            </button>
          </>
        )}

        {/* Confirm */}
        {step === 'confirm' && (
          <div className="space-y-4">
            {transferMutation.isError && (
              <div className="bg-red/10 border border-red rounded-xl p-3 flex items-center gap-2">
                <AlertCircle size={20} className="text-red" />
                <span className="text-red text-sm">{(transferMutation.error as Error)?.message}</span>
              </div>
            )}

            <div className="bg-card rounded-xl p-4 space-y-3 border border-border">
              <div className="flex justify-between">
                <span className="text-text-muted">{t('recipient')}</span>
                <span>@{selectedRecipient?.oltin_id}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-muted">{L('Manzil', 'Адрес', 'Address')}</span>
                {resolving ? (
                  <span className="text-text-muted text-sm">…</span>
                ) : recipientAddress ? (
                  <span className="font-mono text-sm">{truncate(recipientAddress)}</span>
                ) : (
                  <span className="text-red text-sm">
                    {L('Hamyon yoq', 'Нет кошелька', 'No wallet')}
                  </span>
                )}
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">{t('amount')}</span>
                <span className="text-gold font-semibold">{amount} OLTIN</span>
              </div>
              <div className="border-t border-border pt-3 text-text-muted text-xs">
                {L(
                  'Komissiyasiz — tarmoq gazi ETH da tolanadi',
                  'Без комиссии — сетевой газ оплачивается в ETH',
                  'No fee — network gas is paid in ETH',
                )}
              </div>
            </div>

            {isSelf && (
              <div className="text-red text-sm text-center">
                {L("O'zingizga yubora olmaysiz", 'Нельзя отправить самому себе', 'Cannot send to yourself')}
              </div>
            )}

            <button
              onClick={() => transferMutation.mutate()}
              disabled={!canConfirm}
              className="w-full bg-gold text-background py-4 rounded-xl font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {transferMutation.isPending ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  {L('Yuborilmoqda…', 'Отправка…', 'Sending…')}
                </>
              ) : (
                t('confirm')
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
