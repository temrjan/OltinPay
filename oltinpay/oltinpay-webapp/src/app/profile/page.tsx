'use client';

import { useState, useEffect } from 'react';
import { User, Globe, ChevronRight, LogOut, Bot, Copy, Check, Star, List, Info } from 'lucide-react';
import Link from 'next/link';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { useAppStore } from '@/stores/app';
import { api } from '@/lib/api';

export default function ProfilePage() {
  const { user: tgUser, hapticFeedback, webApp } = useTelegram();
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const user = useAppStore((state) => state.user);
  const language = useAppStore((state) => state.language);
  const setLanguage = useAppStore((state) => state.setLanguage);
  const logout = useAppStore((state) => state.logout);

  const [copied, setCopied] = useState(false);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);

  // Get Telegram user photo
  useEffect(() => {
    if (tgUser?.photo_url) {
      setPhotoUrl(tgUser.photo_url);
    }
  }, [tgUser]);

  const updateLanguageMutation = useMutation({
    mutationFn: (lang: string) => api.updateMe({ language: lang }),
    onSuccess: (_, lang) => {
      setLanguage(lang);
      localStorage.setItem('oltinpay_lang', lang);
      queryClient.invalidateQueries({ queryKey: ['user'] });
      hapticFeedback('success');
    },
  });

  const languages = [
    { code: 'uz', label: "O'zbekcha", flag: '🇺🇿' },
    { code: 'ru', label: 'Русский', flag: '🇷🇺' },
    { code: 'en', label: 'English', flag: '🇬🇧' },
  ];

  const menuItems = [
    { href: '/aylin', icon: Bot, label: t('aylinAssistant'), color: 'text-gold' },
    { href: '/favorites', icon: Star, label: t('favorites'), color: 'text-gold' },
    { href: '/history', icon: List, label: t('allOperations'), color: 'text-text-muted' },
  ];

  const handleLanguageChange = (lang: string) => {
    updateLanguageMutation.mutate(lang);
  };

  const copyOltinId = () => {
    if (user?.oltin_id) {
      navigator.clipboard.writeText(`@${user.oltin_id}`);
      setCopied(true);
      hapticFeedback('success');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleLogout = () => {
    hapticFeedback('medium');
    logout();
    webApp?.close();
  };

  const displayName = tgUser?.first_name
    ? `${tgUser.first_name}${tgUser.last_name ? ` ${tgUser.last_name}` : ''}`
    : 'User';

  const isCustomOltinId = user?.oltin_id && !user.oltin_id.startsWith('user_');

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">{t('profile')}</h1>

      {/* Profile header */}
      <div className="bg-card rounded-xl border border-border p-6 flex flex-col items-center">
        {/* Avatar with Telegram photo */}
        <div className="w-24 h-24 rounded-full overflow-hidden bg-gold/20 flex items-center justify-center mb-4">
          {photoUrl ? (
            <img
              src={photoUrl}
              alt={displayName}
              className="w-full h-full object-cover"
              onError={() => setPhotoUrl(null)}
            />
          ) : (
            <User className="text-gold" size={40} />
          )}
        </div>

        {/* Name */}
        <div className="text-xl font-semibold mb-1">{displayName}</div>

        {/* OltinPay ID with copy */}
        <button
          onClick={copyOltinId}
          className="flex items-center gap-2 text-gold hover:opacity-80 transition-opacity"
        >
          <span className="text-lg">@{user?.oltin_id || '...'}</span>
          {copied ? (
            <Check size={16} className="text-green" />
          ) : (
            <Copy size={16} />
          )}
        </button>

        {/* Telegram username */}
        {tgUser?.username && (
          <div className="text-text-muted text-sm mt-1">
            Telegram: @{tgUser.username}
          </div>
        )}

        {/* Set custom OltinPay ID */}
        {!isCustomOltinId && (
          <Link
            href="/set-oltin-id"
            className="mt-3 text-sm text-gold underline"
          >
            {t('setCustomId')}
          </Link>
        )}
      </div>

      {/* Language selector */}
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex items-center gap-3 mb-3">
          <Globe size={20} className="text-text-muted" />
          <span className="font-semibold">{t('language')}</span>
        </div>
        <div className="flex gap-2">
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => handleLanguageChange(lang.code)}
              disabled={updateLanguageMutation.isPending}
              className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                language === lang.code
                  ? 'bg-gold text-background'
                  : 'bg-background border border-border text-text-muted hover:border-gold'
              }`}
            >
              <span className="mr-1">{lang.flag}</span>
              {lang.label}
            </button>
          ))}
        </div>
      </div>

      {/* Menu items */}
      <div className="bg-card rounded-xl border border-border divide-y divide-border">
        {menuItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => hapticFeedback('light')}
            className="flex items-center justify-between p-4"
          >
            <div className="flex items-center gap-3">
              <item.icon size={20} className={item.color} />
              <span>{item.label}</span>
            </div>
            <ChevronRight size={20} className="text-text-muted" />
          </Link>
        ))}
      </div>

      {/* About */}
      <div className="bg-card rounded-xl border border-border">
        <Link href="/about" onClick={() => hapticFeedback('light')} className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <Info size={20} className="text-text-muted" />
            <span>{t('about')}</span>
          </div>
          <ChevronRight size={20} className="text-text-muted" />
        </Link>
      </div>

      {/* Logout button */}
      <button
        onClick={handleLogout}
        className="w-full bg-red/10 text-red py-4 rounded-xl font-semibold flex items-center justify-center gap-2"
      >
        <LogOut size={20} />
        {t('logout')}
      </button>

      {/* App info */}
      <div className="text-center text-text-muted text-xs space-y-1">
        <div>OltinPay v1.0.0</div>
        <div>Powered by zkSync Era</div>
      </div>
    </div>
  );
}
