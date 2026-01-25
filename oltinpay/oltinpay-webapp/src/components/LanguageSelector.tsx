'use client';

import { useCallback } from 'react';
import { useAppStore } from '@/stores/app';

interface Language {
  code: string;
  name: string;
  flag: string;
}

const LANGUAGES: Language[] = [
  { code: 'uz', name: "O'zbekcha", flag: '🇺🇿' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
];

export function LanguageSelector() {
  const setLanguage = useAppStore((state) => state.setLanguage);

  const handleSelect = useCallback((code: string) => {
    setLanguage(code);
    // Store in localStorage for persistence
    if (typeof window !== 'undefined') {
      localStorage.setItem('oltinpay_lang', code);
    }
  }, [setLanguage]);

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      {/* Logo */}
      <div className="mb-8 text-center">
        <div className="text-6xl mb-4">🥇</div>
        <h1 className="text-3xl font-bold text-gold">OltinPay</h1>
        <p className="text-text-muted mt-2">Tokenized Gold Trading</p>
      </div>

      {/* Language Selection */}
      <div className="w-full max-w-sm">
        <p className="text-center text-text-muted mb-4">Tilni tanlang / Выберите язык</p>

        <div className="space-y-3">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => handleSelect(lang.code)}
              className="w-full bg-card border border-border rounded-xl p-4 flex items-center gap-4 hover:border-gold transition-colors"
            >
              <span className="text-3xl">{lang.flag}</span>
              <span className="text-lg font-semibold text-text-primary">{lang.name}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
