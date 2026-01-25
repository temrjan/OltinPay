'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAppStore } from '@/stores/app';
import { LanguageSelector } from '@/components/LanguageSelector';

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
  const searchParams = useSearchParams();
  const language = useAppStore((state) => state.language);
  const setLanguage = useAppStore((state) => state.setLanguage);
  const initFromStorage = useAppStore((state) => state.initFromStorage);

  useEffect(() => {
    const langParam = searchParams.get('lang');
    if (langParam && ['uz', 'ru', 'en'].includes(langParam)) {
      setLanguage(langParam);
      localStorage.setItem('oltinpay_lang', langParam);
    } else {
      initFromStorage();
    }
    setIsLoading(false);
  }, [searchParams, setLanguage, initFromStorage]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-gold" />
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
