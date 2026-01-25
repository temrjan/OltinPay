'use client';

import { useAppStore } from '@/stores/app';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import Link from 'next/link';
import { Bot, Star, List, Globe, Info, ChevronRight } from 'lucide-react';

export default function ProfilePage() {
  const language = useAppStore((state) => state.language);
  const setLanguage = useAppStore((state) => state.setLanguage);
  const { user, hapticFeedback } = useTelegram();
  const { t } = useTranslation();

  const menuItems = [
    { href: '/aylin', icon: Bot, label: t('aylinAssistant'), color: 'text-gold' },
    { href: '/favorites', icon: Star, label: t('favorites'), color: 'text-gold' },
    { href: '/history', icon: List, label: t('allOperations'), color: 'text-text-muted' },
  ];

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLang = e.target.value;
    setLanguage(newLang);
    localStorage.setItem('oltinpay_lang', newLang);
    hapticFeedback('selection');
  };

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">{t('profile')}</h1>

      <div className="bg-card rounded-xl border border-border p-4 flex items-center gap-4">
        <div className="w-16 h-16 rounded-full bg-gold/20 flex items-center justify-center text-2xl">👤</div>
        <div>
          <div className="text-xl font-semibold">{user?.first_name || 'User'}</div>
          <div className="text-text-muted text-sm">@{user?.username || 'anonymous'}</div>
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border space-y-1 p-2">
        {menuItems.map(({ href, icon: Icon, label, color }) => (
          <Link
            key={href}
            href={href}
            onClick={() => hapticFeedback('selection')}
            className="flex items-center justify-between p-3 rounded-xl hover:bg-background transition-colors"
          >
            <div className="flex items-center gap-3">
              <Icon className={color} size={22} />
              <span>{label}</span>
            </div>
            <ChevronRight className="text-text-muted" size={20} />
          </Link>
        ))}
      </div>

      <div className="bg-card rounded-xl border border-border">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <Globe className="text-text-muted" size={22} />
            <span>{t('language')}</span>
          </div>
          <select
            value={language || 'uz'}
            onChange={handleLanguageChange}
            className="bg-background border border-border rounded-lg px-3 py-2 text-sm"
          >
            <option value="uz">Ozbek 🇺🇿</option>
            <option value="ru">Русский 🇷🇺</option>
            <option value="en">English 🇬🇧</option>
          </select>
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border">
        <Link href="/about" onClick={() => hapticFeedback('selection')} className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <Info className="text-text-muted" size={22} />
            <span>{t('about')}</span>
          </div>
          <ChevronRight className="text-text-muted" size={20} />
        </Link>
      </div>

      <div className="text-center text-text-muted text-xs pt-4">
        <div>OltinPay v0.1.0</div>
        <div>© 2026 OltinPay</div>
      </div>
    </div>
  );
}
