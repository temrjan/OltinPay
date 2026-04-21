'use client';

import {useTranslation} from '@/hooks/useTranslation';

export function DemoBadge() {
  const {t} = useTranslation();
  return (
    <div className="flex items-center justify-center gap-2 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-xs px-3 py-1.5 rounded-md">
      <span className="font-semibold">{t('demoBadge')}</span>
      <span className="opacity-70">·</span>
      <span className="opacity-90">{t('demoBadgeNote')}</span>
    </div>
  );
}
