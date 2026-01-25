'use client';

import { useState } from 'react';
import { ArrowLeft, Copy, Check, QrCode } from 'lucide-react';
import Link from 'next/link';
import { useTelegram } from '@/hooks/useTelegram';
import { useTranslation } from '@/hooks/useTranslation';
import { useAppStore } from '@/stores/app';

export default function ReceivePage() {
  const { hapticFeedback } = useTelegram();
  const { t, language } = useTranslation();
  const user = useAppStore((state) => state.user);
  const [copied, setCopied] = useState(false);

  const oltinId = user?.oltin_id ? `@${user.oltin_id}` : '';

  const copyToClipboard = () => {
    if (oltinId) {
      navigator.clipboard.writeText(oltinId);
      setCopied(true);
      hapticFeedback('success');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getLabel = (key: string) => {
    const labels: Record<string, Record<string, string>> = {
      yourOltinId: { uz: 'Sizning OLTIN ID', ru: 'Ваш OLTIN ID', en: 'Your OLTIN ID' },
      shareToReceive: { uz: 'Pul olish uchun ID ni ulashing', ru: 'Поделитесь ID чтобы получить средства', en: 'Share your ID to receive funds' },
      copied: { uz: 'Nusxalandi!', ru: 'Скопировано!', en: 'Copied!' },
      copyId: { uz: 'ID ni nusxalash', ru: 'Скопировать ID', en: 'Copy ID' },
      howToReceive: { uz: 'Qanday qilib pul olish', ru: 'Как получить средства', en: 'How to receive' },
      step1: { uz: 'OLTIN ID ni jonatuvchiga yuboring', ru: 'Отправьте OLTIN ID отправителю', en: 'Share your OLTIN ID with sender' },
      step2: { uz: 'Jonatuvchi ID ni kiritadi', ru: 'Отправитель вводит ID', en: 'Sender enters your ID' },
      step3: { uz: 'Mablaglar hisobga tushadi', ru: 'Средства поступят на счёт', en: 'Funds arrive to your account' },
    };
    return labels[key]?.[language] || labels[key]?.['en'] || key;
  };

  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex items-center gap-3 p-4 border-b border-border">
        <Link href="/wallet" className="text-text-muted">
          <ArrowLeft size={24} />
        </Link>
        <h1 className="text-lg font-semibold">{t('receive')}</h1>
      </div>

      <div className="flex-1 p-4 space-y-4">
        <div className="bg-card rounded-xl border border-border p-8 flex flex-col items-center">
          <div className="w-32 h-32 bg-background rounded-xl flex items-center justify-center mb-4 border border-border">
            <QrCode size={64} className="text-gold" />
          </div>
          <div className="text-text-muted text-sm mb-2">{getLabel('yourOltinId')}</div>
          <div className="text-2xl font-bold text-gold">{oltinId}</div>
        </div>

        <button
          onClick={copyToClipboard}
          className="w-full bg-gold text-background py-4 rounded-xl font-semibold flex items-center justify-center gap-2"
        >
          {copied ? (
            <>
              <Check size={20} />
              {getLabel('copied')}
            </>
          ) : (
            <>
              <Copy size={20} />
              {getLabel('copyId')}
            </>
          )}
        </button>

        <div className="bg-card rounded-xl border border-border p-4">
          <h3 className="font-semibold mb-3">{getLabel('howToReceive')}</h3>
          <div className="space-y-2 text-sm text-text-muted">
            <p>1. {getLabel('step1')}</p>
            <p>2. {getLabel('step2')}</p>
            <p>3. {getLabel('step3')}</p>
          </div>
        </div>

        <p className="text-text-muted text-xs text-center">{getLabel('shareToReceive')}</p>
      </div>
    </div>
  );
}
