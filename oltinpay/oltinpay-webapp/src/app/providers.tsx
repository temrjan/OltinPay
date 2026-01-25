'use client';

import { useEffect, useState, Suspense, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAppStore } from '@/stores/app';
import { LanguageSelector } from '@/components/LanguageSelector';
import { api } from '@/lib/api';

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
