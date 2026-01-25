'use client';

import { useAppStore } from '@/stores/app';
import { translations, type Language, type TranslationKey } from '@/lib/i18n';

export function useTranslation() {
  const language = useAppStore((state) => state.language) as Language | null;
  const lang = language || 'uz';

  const t = (key: TranslationKey): string => {
    return translations[lang]?.[key] || translations.uz[key] || key;
  };

  return { t, language: lang };
}
