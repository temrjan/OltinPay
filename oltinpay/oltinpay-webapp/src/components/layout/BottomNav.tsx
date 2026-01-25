'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Wallet, BarChart2, Diamond, User } from 'lucide-react';
import { useTranslation } from '@/hooks/useTranslation';

export function BottomNav() {
  const pathname = usePathname();
  const { t } = useTranslation();

  const navItems = [
    { href: '/wallet', icon: Wallet, label: t('wallet') },
    { href: '/exchange', icon: BarChart2, label: t('exchange') },
    { href: '/staking', icon: Diamond, label: t('staking') },
    { href: '/profile', icon: User, label: t('profile') },
  ];

  return (
    <nav className="bottom-nav">
      <div className="flex justify-around items-center h-14">
        {navItems.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center justify-center w-16 h-full transition-colors ${
                isActive ? 'text-gold' : 'text-text-muted'
              }`}
            >
              <Icon size={24} aria-hidden />
              <span className="text-[10px] mt-1">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
