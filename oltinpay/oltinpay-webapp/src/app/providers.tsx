'use client';

import { useEffect, useState, Suspense, useCallback } from 'react';
import { useSearchParams, usePathname, useRouter } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAppStore } from '@/stores/app';
import { useWalletStore } from '@/stores/wallet';
import { LanguageSelector } from '@/components/LanguageSelector';
import { PinUnlock } from '@/components/PinUnlock';
import { useTranslation } from '@/hooks/useTranslation';
import { api, ApiError } from '@/lib/api';
import { hasWallet as checkWalletStorage, removeEncryptedWallet } from '@/lib/wallet';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      retry: 1,
    },
  },
});

function AppContent({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const searchParams = useSearchParams();

  const language = useAppStore((state) => state.language);
  const setLanguage = useAppStore((state) => state.setLanguage);
  const setToken = useAppStore((state) => state.setToken);
  const setUser = useAppStore((state) => state.setUser);
  const initFromStorage = useAppStore((state) => state.initFromStorage);
  const token = useAppStore((state) => state.token);

  const authenticate = useCallback(async () => {
    // Check if running in Telegram WebApp
    const tg = typeof window !== 'undefined' ? (window as any).Telegram?.WebApp : null;

    if (tg?.initData) {
      try {
        const result = await api.authenticate(tg.initData);
        api.setToken(result.access_token);
        setToken(result.access_token);
        setUser(result.user);
        localStorage.setItem('oltinpay_token', result.access_token);

        // Set language from user if not set
        if (result.user?.language) {
          setLanguage(result.user.language);
          localStorage.setItem('oltinpay_lang', result.user.language);
        }
      } catch (err) {
        console.error('Auth error:', err);
        setAuthError(err instanceof Error ? err.message : 'Authentication failed');
      }
    } else {
      // Not in Telegram - try to use saved token
      initFromStorage();
      const savedToken = localStorage.getItem('oltinpay_token');
      if (savedToken) {
        api.setToken(savedToken);
      }
    }
  }, [setToken, setUser, setLanguage, initFromStorage]);

  useEffect(() => {
    const init = async () => {
      // Handle language from URL param
      const langParam = searchParams.get('lang');
      if (langParam && ['uz', 'ru', 'en'].includes(langParam)) {
        setLanguage(langParam);
        localStorage.setItem('oltinpay_lang', langParam);
      } else {
        const savedLang = localStorage.getItem('oltinpay_lang');
        if (savedLang) {
          setLanguage(savedLang);
        }
      }

      // Authenticate
      await authenticate();

      setIsLoading(false);
    };

    init();
  }, [searchParams, setLanguage, authenticate]);

  // Sync token with API client when it changes
  useEffect(() => {
    if (token) {
      api.setToken(token);
    }
  }, [token]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-gold" />
      </div>
    );
  }

  if (authError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <div className="text-red text-center mb-4">Auth Error: {authError}</div>
        <button
          onClick={() => { setAuthError(null); authenticate(); }}
          className="bg-gold text-background px-4 py-2 rounded-lg"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!language) {
    return <LanguageSelector />;
  }

  return <WalletGate>{children}</WalletGate>;
}

function WalletGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const account = useWalletStore((s) => s.account);
  const isExpired = useWalletStore((s) => s.isExpired);
  const lock = useWalletStore((s) => s.lock);
  const walletPresent = useWalletStore((s) => s.hasWallet);
  const setHasWallet = useWalletStore((s) => s.setHasWallet);
  const reset = useWalletStore((s) => s.reset);
  const { t } = useTranslation();
  const [checkFailed, setCheckFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [registeredAddress, setRegisteredAddress] = useState<string | null>(null);
  const [registerError, setRegisterError] = useState<null | 'retryable' | 'conflict'>(null);
  const [regAttempt, setRegAttempt] = useState(0);

  // Onboarding routes are gateless — user is creating or restoring a wallet.
  const isOnboarding = pathname?.startsWith('/onboarding') ?? false;

  // Seed presence from storage while still unknown. On a storage READ error we do
  // NOT collapse "couldn't check" into "absent": that would route an existing-wallet
  // user to onboarding, where a fresh mnemonic silently overwrites the (non-custodial)
  // blob — irreversible loss. Instead surface a retry screen and keep presence unknown.
  useEffect(() => {
    if (walletPresent !== null) return;
    let cancelled = false;
    (async () => {
      try {
        const present = await checkWalletStorage();
        if (!cancelled) setHasWallet(present);
      } catch (err) {
        console.error('Wallet presence check failed:', err);
        if (!cancelled) setCheckFailed(true);
      }
    })();
    return () => { cancelled = true; };
  }, [walletPresent, setHasWallet, attempt]);

  // Auto-lock when the in-memory session expires
  useEffect(() => {
    if (account !== null && isExpired()) {
      lock();
    }
  }, [account, isExpired, lock]);

  // Redirect to onboarding if no wallet exists
  useEffect(() => {
    if (walletPresent === false && !isOnboarding) {
      router.replace('/onboarding');
    }
  }, [walletPresent, isOnboarding, router]);

  // Bind the wallet address to the backend once the session is unlocked. Runs on
  // every unlock (onboarding/restore/PinUnlock) and is idempotent (backend returns
  // 200 when the same address is already bound), so wallets created before this
  // shipped self-heal on their next unlock. A 409 means the account is bound to a
  // DIFFERENT wallet (a rejected restore) — a terminal, non-retryable state.
  useEffect(() => {
    if (account === null || registeredAddress === account.address || registerError) return;
    const addr = account.address;
    let cancelled = false;
    (async () => {
      try {
        await api.registerWallet(addr);
        if (!cancelled) setRegisteredAddress(addr);
      } catch (err) {
        if (cancelled) return;
        setRegisterError(
          err instanceof ApiError && err.status === 409 ? 'conflict' : 'retryable'
        );
      }
    })();
    return () => { cancelled = true; };
  }, [account, registeredAddress, registerError, regAttempt]);

  if (isOnboarding) {
    return <>{children}</>;
  }

  // Storage read failed — never silently route to onboarding (that risks
  // overwriting an existing wallet). Offer an explicit retry instead.
  if (checkFailed) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4 gap-4">
        <div className="text-text-muted text-center">{t('walletCheckFailed')}</div>
        <button
          onClick={() => { setCheckFailed(false); setAttempt((a) => a + 1); }}
          className="bg-gold text-background px-4 py-2 rounded-lg font-medium"
        >
          {t('retry')}
        </button>
      </div>
    );
  }

  if (walletPresent === null) {
    return <LoadingSpinner />;
  }

  if (walletPresent === false) {
    return <LoadingSpinner />; // briefly while redirect happens
  }

  if (account === null) {
    return <PinUnlock />;
  }

  // Backend rejected the address: the account is bound to a DIFFERENT wallet
  // (a restore of the wrong seed). Non-retryable — wipe the wrong local blob and
  // send the user back to onboarding, else they'd be stuck on a wallet that can
  // never register.
  if (registerError === 'conflict') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4 gap-4">
        <div className="text-text-muted text-center">{t('walletConflict')}</div>
        <button
          onClick={async () => {
            setRegisterError(null);
            await removeEncryptedWallet();
            reset();
          }}
          className="bg-gold text-background px-4 py-2 rounded-lg font-medium"
        >
          {t('startOver')}
        </button>
      </div>
    );
  }

  // Registration failed for a transient reason (network / 5xx) — offer a retry.
  if (registerError === 'retryable') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4 gap-4">
        <div className="text-text-muted text-center">{t('walletRegisterFailed')}</div>
        <button
          onClick={() => { setRegisterError(null); setRegAttempt((a) => a + 1); }}
          className="bg-gold text-background px-4 py-2 rounded-lg font-medium"
        >
          {t('retry')}
        </button>
      </div>
    );
  }

  // Registration in flight — don't show wallet content (balances/claim would 400)
  // until the address is bound on the backend.
  if (registeredAddress !== account.address) {
    return <LoadingSpinner />;
  }

  return <>{children}</>;
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-gold" />
    </div>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={<LoadingSpinner />}>
        <AppContent>{children}</AppContent>
      </Suspense>
    </QueryClientProvider>
  );
}
