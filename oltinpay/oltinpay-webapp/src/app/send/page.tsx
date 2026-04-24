'use client';

import { useState } from 'react';
import { ArrowLeft, Search, User, CheckCircle, AlertCircle, ArrowRightLeft } from 'lucide-react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { api } from '@/lib/api';
import { useAppStore } from '@/stores/app';

interface UserSearchResult {
  id: string;
  oltin_id: string;
  telegram_id: number;
}

type AccountType = 'wallet' | 'exchange' | 'staking';
type Currency = 'USD' | 'OLTIN';

const ACCOUNT_LABELS: Record<AccountType, Record<string, string>> = {
  wallet: { uz: 'Hamyon', ru: 'Кошелёк', en: 'Wallet' },
  exchange: { uz: 'Birja', ru: 'Биржа', en: 'Exchange' },
  staking: { uz: 'Steyking', ru: 'Стейкинг', en: 'Staking' },
};

export default function SendPage() {
  const { hapticFeedback } = useTelegram();
  const { t, language } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAppStore((state) => state.user);

  // Tab state
  const [activeTab, setActiveTab] = useState<'user' | 'internal'>('user');

  // User transfer state
  const [step, setStep] = useState<'recipient' | 'amount' | 'confirm' | 'success'>('recipient');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRecipient, setSelectedRecipient] = useState<UserSearchResult | null>(null);
  const [amount, setAmount] = useState('');

  // Internal transfer state
  const [fromAccount, setFromAccount] = useState<AccountType>('wallet');
  const [toAccount, setToAccount] = useState<AccountType>('exchange');
  const [currency, setCurrency] = useState<Currency>('USD');
  const [internalAmount, setInternalAmount] = useState('');
  const [internalSuccess, setInternalSuccess] = useState(false);

  // Get balances
  const { data: balancesData } = useQuery({
    queryKey: ['balances'],
    queryFn: () => api.getBalances(),
  });

  // Search users
  const { data: searchResults, isLoading: searching } = useQuery({
    queryKey: ['searchUsers', searchQuery],
    queryFn: () => api.searchUsers(searchQuery),
    enabled: searchQuery.length >= 2,
  });

  // Get recent contacts
  const { data: recentContacts } = useQuery({
    queryKey: ['recentContacts'],
    queryFn: () => api.getRecentContacts(),
  });

  // Get favorites
  const { data: favorites } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => api.getFavorites(),
  });

  // Transfer to user mutation
  const transferMutation = useMutation({
    mutationFn: ({ to_oltin_id, amount }: { to_oltin_id: string; amount: number }) =>
      api.createTransfer(to_oltin_id, amount),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['balances'] });
      queryClient.invalidateQueries({ queryKey: ['transfers'] });
      queryClient.invalidateQueries({ queryKey: ['recentContacts'] });
      setStep('success');
      hapticFeedback('success');
    },
    onError: () => hapticFeedback('error'),
  });

  // Internal transfer mutation
  const internalTransferMutation = useMutation({
    mutationFn: (data: { from_account: string; to_account: string; currency: string; amount: number }) =>
      api.internalTransfer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['balances'] });
      queryClient.invalidateQueries({ queryKey: ['staking'] });
      setInternalSuccess(true);
      setInternalAmount('');
      hapticFeedback('success');
      setTimeout(() => setInternalSuccess(false), 3000);
    },
    onError: () => hapticFeedback('error'),
  });

  // Get balance for account/currency
  const getBalance = (account: AccountType, cur: Currency): number => {
    if (!balancesData) return 0;
    const accountData = (balancesData as any)[account];
    if (!accountData) return 0;
    return Number(accountData[cur.toLowerCase()]) || 0;
  };

  // User transfer balance (OLTIN from wallet)
  const walletOltinBalance = getBalance('wallet', 'OLTIN');
  const fee = amount ? parseFloat(amount) * 0.01 : 0;
  const total = amount ? parseFloat(amount) + fee : 0;

  // Staking only supports OLTIN
  const isStakingInvolved = fromAccount === 'staking' || toAccount === 'staking';
  const effectiveCurrency = isStakingInvolved ? 'OLTIN' : currency;
  const effectiveBalance = getBalance(fromAccount, effectiveCurrency);

  const handleSelectRecipient = (recipient: UserSearchResult) => {
    setSelectedRecipient(recipient);
    setStep('amount');
    hapticFeedback('selection');
  };

  const handleConfirm = () => {
    if (!selectedRecipient || !amount) return;
    transferMutation.mutate({
      to_oltin_id: selectedRecipient.oltin_id,
      amount: parseFloat(amount),
    });
  };

  const handleInternalTransfer = () => {
    if (!internalAmount || fromAccount === toAccount) return;
    internalTransferMutation.mutate({
      from_account: fromAccount,
      to_account: toAccount,
      currency: effectiveCurrency,
      amount: parseFloat(internalAmount),
    });
  };

  const swapAccounts = () => {
    const temp = fromAccount;
    setFromAccount(toAccount);
    setToAccount(temp);
    hapticFeedback('selection');
  };

  const reset = () => {
    setStep('recipient');
    setSearchQuery('');
    setSelectedRecipient(null);
    setAmount('');
  };

  const getAccountLabel = (account: AccountType) => {
    return ACCOUNT_LABELS[account][language] || ACCOUNT_LABELS[account]['en'];
  };

  // Active/inactive button styles for account selection (reference: staking APY card)
  const getAccountButtonStyle = (account: AccountType, selected: AccountType, disabled: boolean) => {
    if (disabled) return 'bg-background/50 border border-border/50 text-text-muted/50 cursor-not-allowed';
    if (account === selected) return 'bg-gold/10 border border-gold text-gold';
    return 'bg-background border border-border text-text-muted hover:border-gold/50';
  };

  const getCurrencyButtonStyle = (cur: Currency, selected: Currency) => {
    if (cur === selected) return 'bg-gold/10 border border-gold text-gold';
    return 'bg-background border border-border text-text-muted hover:border-gold/50';
  };

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
          <button onClick={() => setStep(step === 'confirm' ? 'amount' : 'recipient')} className="text-text-muted">
            <ArrowLeft size={24} />
          </button>
        )}
        <h1 className="text-lg font-semibold">{t('send')}</h1>
      </div>

      {/* Tabs - only show on recipient step */}
      {step === 'recipient' && (
        <div className="flex bg-card m-4 mb-0 rounded-xl p-1 border border-border">
          <button
            onClick={() => { setActiveTab('user'); hapticFeedback('selection'); }}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'user' ? 'bg-gold text-background' : 'text-text-muted'
            }`}
          >
            {language === 'uz' ? 'Foydalanuvchiga' : language === 'ru' ? 'Пользователю' : 'To User'}
          </button>
          <button
            onClick={() => { setActiveTab('internal'); hapticFeedback('selection'); }}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'internal' ? 'bg-gold text-background' : 'text-text-muted'
            }`}
          >
            {language === 'uz' ? 'Hisoblar' : language === 'ru' ? 'Между счетами' : 'Accounts'}
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 p-4 space-y-4">
        {/* ===== USER TRANSFER TAB ===== */}
        {activeTab === 'user' && (
          <>
            {/* Success state */}
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

            {/* Recipient step */}
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

                {/* Search results */}
                {searching && (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-gold" />
                  </div>
                )}

                {searchResults && searchResults.length > 0 && (
                  <div className="space-y-2">
                    {searchResults.filter((u: UserSearchResult) => u.id !== user?.id).map((u: UserSearchResult) => (
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

                {/* Favorites */}
                {!searchQuery && favorites && favorites.length > 0 && (
                  <div>
                    <h3 className="text-text-muted text-sm mb-2">{t('favorites')}</h3>
                    <div className="space-y-2">
                      {favorites.map((f: any) => (
                        <button
                          key={f.id}
                          onClick={() => handleSelectRecipient({ id: f.contact_user_id, oltin_id: f.contact_oltin_id, telegram_id: 0 })}
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

                {/* Recent contacts */}
                {!searchQuery && recentContacts && recentContacts.length > 0 && (
                  <div>
                    <h3 className="text-text-muted text-sm mb-2">{t('recent')}</h3>
                    <div className="space-y-2">
                      {recentContacts.slice(0, 5).map((c: any) => (
                        <button
                          key={c.user_id}
                          onClick={() => handleSelectRecipient({ id: c.user_id, oltin_id: c.oltin_id, telegram_id: 0 })}
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

            {/* Amount step */}
            {step === 'amount' && (
              <>
                <div className="text-center text-text-muted text-sm mb-2">
                  {t('to')}: @{selectedRecipient?.oltin_id}
                </div>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.0000"
                  className="w-full bg-background border border-border rounded-xl px-4 py-3 text-2xl text-center focus:outline-none focus:border-gold"
                />
                <div className="text-center">
                  <button onClick={() => setAmount(walletOltinBalance.toString())} className="text-gold text-sm">
                    {t('available')}: {walletOltinBalance.toFixed(4)} OLTIN
                  </button>
                </div>
                <button
                  onClick={() => { setStep('confirm'); hapticFeedback('medium'); }}
                  disabled={!amount || parseFloat(amount) <= 0 || parseFloat(amount) > walletOltinBalance}
                  className="w-full bg-gold text-background py-4 rounded-xl font-semibold disabled:opacity-50"
                >
                  {t('continue')}
                </button>
              </>
            )}

            {/* Confirm step */}
            {step === 'confirm' && (
              <div className="space-y-4">
                {/* Error */}
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
                  <div className="flex justify-between">
                    <span className="text-text-muted">{t('amount')}</span>
                    <span className="text-gold font-semibold">{amount} OLTIN</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">{t('fee')} (1%)</span>
                    <span>{fee.toFixed(6)} OLTIN</span>
                  </div>
                  <div className="border-t border-border pt-3 flex justify-between">
                    <span className="font-semibold">{t('total')}</span>
                    <span className="font-semibold">{total.toFixed(6)} OLTIN</span>
                  </div>
                </div>
                <button
                  onClick={handleConfirm}
                  disabled={transferMutation.isPending}
                  className="w-full bg-gold text-background py-4 rounded-xl font-semibold disabled:opacity-50"
                >
                  {transferMutation.isPending ? '...' : t('confirm')}
                </button>
              </div>
            )}
          </>
        )}

        {/* ===== INTERNAL TRANSFER TAB ===== */}
        {activeTab === 'internal' && step === 'recipient' && (
          <div className="space-y-4">
            {/* Success message */}
            {internalSuccess && (
              <div className="bg-green/10 border border-green rounded-xl p-3 flex items-center gap-2">
                <CheckCircle size={20} className="text-green" />
                <span className="text-green text-sm">
                  {language === 'uz' ? "Muvaffaqiyatli o'tkazildi!" : language === 'ru' ? 'Успешно переведено!' : 'Transfer successful!'}
                </span>
              </div>
            )}

            {/* Error message */}
            {internalTransferMutation.isError && (
              <div className="bg-red/10 border border-red rounded-xl p-3 flex items-center gap-2">
                <AlertCircle size={20} className="text-red" />
                <span className="text-red text-sm">{(internalTransferMutation.error as Error)?.message}</span>
              </div>
            )}

            {/* From account */}
            <div className="bg-card rounded-xl p-4 border border-border">
              <label className="text-text-muted text-sm mb-2 block">
                {language === 'uz' ? 'Qayerdan' : language === 'ru' ? 'Откуда' : 'From'}
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(['wallet', 'exchange', 'staking'] as AccountType[]).map((acc) => (
                  <button
                    key={acc}
                    onClick={() => { if (acc !== toAccount) { setFromAccount(acc); hapticFeedback('selection'); } }}
                    disabled={acc === toAccount}
                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${getAccountButtonStyle(acc, fromAccount, acc === toAccount)}`}
                  >
                    {getAccountLabel(acc)}
                  </button>
                ))}
              </div>
            </div>

            {/* Swap button */}
            <div className="flex justify-center">
              <button
                onClick={swapAccounts}
                className="p-2 rounded-full bg-card border border-border hover:border-gold transition-colors"
              >
                <ArrowRightLeft size={20} className="text-gold rotate-90" />
              </button>
            </div>

            {/* To account */}
            <div className="bg-card rounded-xl p-4 border border-border">
              <label className="text-text-muted text-sm mb-2 block">
                {language === 'uz' ? 'Qayerga' : language === 'ru' ? 'Куда' : 'To'}
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(['wallet', 'exchange', 'staking'] as AccountType[]).map((acc) => (
                  <button
                    key={acc}
                    onClick={() => { if (acc !== fromAccount) { setToAccount(acc); hapticFeedback('selection'); } }}
                    disabled={acc === fromAccount}
                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${getAccountButtonStyle(acc, toAccount, acc === fromAccount)}`}
                  >
                    {getAccountLabel(acc)}
                  </button>
                ))}
              </div>
            </div>

            {/* Currency selector (hidden if staking involved) */}
            {!isStakingInvolved && (
              <div className="bg-card rounded-xl p-4 border border-border">
                <label className="text-text-muted text-sm mb-2 block">
                  {language === 'uz' ? 'Valyuta' : language === 'ru' ? 'Валюта' : 'Currency'}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {(['USD', 'OLTIN'] as Currency[]).map((cur) => (
                    <button
                      key={cur}
                      onClick={() => { setCurrency(cur); hapticFeedback('selection'); }}
                      className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${getCurrencyButtonStyle(cur, currency)}`}
                    >
                      {cur}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Staking notice */}
            {isStakingInvolved && (
              <div className="text-text-muted text-sm text-center">
                {language === 'uz' ? 'Steyking faqat OLTIN qabul qiladi' :
                 language === 'ru' ? 'Стейкинг поддерживает только OLTIN' :
                 'Staking only supports OLTIN'}
              </div>
            )}

            {/* Amount input */}
            <div className="bg-card rounded-xl p-4 space-y-3 border border-border">
              <label className="text-text-muted text-sm block">{t('amount')}</label>
              <input
                type="number"
                value={internalAmount}
                onChange={(e) => setInternalAmount(e.target.value)}
                placeholder="0.00"
                className="w-full bg-background border border-border rounded-xl px-4 py-3 text-xl focus:outline-none focus:border-gold"
              />
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">{t('available')}:</span>
                <button
                  onClick={() => setInternalAmount(effectiveBalance.toString())}
                  className="text-gold"
                >
                  {effectiveBalance.toFixed(effectiveCurrency === 'USD' ? 2 : 4)} {effectiveCurrency}
                </button>
              </div>
            </div>

            {/* Transfer button */}
            <button
              onClick={handleInternalTransfer}
              disabled={
                !internalAmount ||
                parseFloat(internalAmount) <= 0 ||
                parseFloat(internalAmount) > effectiveBalance ||
                fromAccount === toAccount ||
                internalTransferMutation.isPending
              }
              className="w-full bg-gold text-background py-4 rounded-xl font-semibold disabled:opacity-50"
            >
              {internalTransferMutation.isPending ? '...' :
               language === 'uz' ? "O'tkazish" : language === 'ru' ? 'Перевести' : 'Transfer'}
            </button>

            {/* Info */}
            <div className="text-center text-text-muted text-xs">
              {language === 'uz' ? "Hisoblar orasida komissiyasiz" :
               language === 'ru' ? 'Между счетами без комиссии' :
               'No fee for internal transfers'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
