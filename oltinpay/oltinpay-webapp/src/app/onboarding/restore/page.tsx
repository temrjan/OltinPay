'use client';

import {useState} from 'react';
import {useRouter} from 'next/navigation';
import Link from 'next/link';

import {useTranslation} from '@/hooks/useTranslation';
import {useWalletStore} from '@/stores/wallet';
import {DemoBadge} from '@/components/DemoBadge';
import {
  encryptMnemonic,
  isValidMnemonic,
  mnemonicToHDAccount,
  saveEncryptedWallet,
} from '@/lib/wallet';

export default function RestorePage() {
  const router = useRouter();
  const {t} = useTranslation();
  const unlock = useWalletStore((s) => s.unlock);

  const [mnemonic, setMnemonic] = useState('');
  const [pin, setPin] = useState('');
  const [pinConfirm, setPinConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const trimmed = mnemonic.trim().toLowerCase().replace(/\s+/g, ' ');
    if (!isValidMnemonic(trimmed)) {
      setError(t('seedInvalid'));
      return;
    }
    if (pin.length < 4) {
      setError(t('pinTooShort'));
      return;
    }
    if (pin !== pinConfirm) {
      setError(t('pinMismatch'));
      return;
    }
    setIsSaving(true);
    try {
      const blob = await encryptMnemonic(trimmed, pin);
      await saveEncryptedWallet(blob);
      const account = mnemonicToHDAccount(trimmed);
      unlock(account);
      router.push('/wallet');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restore wallet');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 pb-24">
      <div className="max-w-md mx-auto space-y-6">
        <DemoBadge />

        <h1 className="text-2xl font-bold text-text-primary">{t('restoreTitle')}</h1>
        <p className="text-text-secondary text-sm">{t('restoreDescription')}</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={mnemonic}
            onChange={(e) => setMnemonic(e.target.value)}
            placeholder={t('seedPlaceholder')}
            rows={4}
            autoCapitalize="none"
            autoComplete="off"
            className="w-full px-4 py-3 bg-card border border-border rounded-lg font-mono text-sm focus:outline-none focus:border-gold"
          />

          <input
            type="password"
            inputMode="numeric"
            maxLength={12}
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            placeholder={t('pin')}
            className="w-full px-4 py-3 bg-card border border-border rounded-lg text-center text-2xl tracking-[0.5em] focus:outline-none focus:border-gold"
          />
          <input
            type="password"
            inputMode="numeric"
            maxLength={12}
            value={pinConfirm}
            onChange={(e) => setPinConfirm(e.target.value)}
            placeholder={t('pinConfirm')}
            className="w-full px-4 py-3 bg-card border border-border rounded-lg text-center text-2xl tracking-[0.5em] focus:outline-none focus:border-gold"
          />

          {error !== null && <p className="text-red text-sm">{error}</p>}

          <button
            type="submit"
            disabled={isSaving}
            className="w-full bg-gold text-background py-3 rounded-lg font-semibold disabled:opacity-50"
          >
            {isSaving ? t('loading') : t('restore')}
          </button>
        </form>

        <div className="text-center">
          <Link href="/onboarding" className="text-text-secondary text-sm underline">
            {t('back')}
          </Link>
        </div>
      </div>
    </div>
  );
}
