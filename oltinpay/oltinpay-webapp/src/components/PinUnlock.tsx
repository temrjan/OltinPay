'use client';

import {useState} from 'react';
import {Lock} from 'lucide-react';

import {useTranslation} from '@/hooks/useTranslation';
import {useWalletStore} from '@/stores/wallet';
import {decryptMnemonic, loadEncryptedWallet, mnemonicToHDAccount} from '@/lib/wallet';

const MAX_PIN_LENGTH = 12;

export function PinUnlock() {
  const {t} = useTranslation();
  const unlock = useWalletStore((s) => s.unlock);
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isUnlocking, setIsUnlocking] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsUnlocking(true);
    try {
      const blob = await loadEncryptedWallet();
      if (!blob) {
        setError(t('walletNotFound'));
        return;
      }
      const mnemonic = await decryptMnemonic(blob, pin);
      const account = mnemonicToHDAccount(mnemonic);
      unlock(account);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unlock failed');
    } finally {
      setIsUnlocking(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background p-6">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="bg-gold/10 p-4 rounded-full mb-4">
            <Lock className="w-8 h-8 text-gold" />
          </div>
          <h1 className="text-2xl font-bold text-text-primary">{t('enterPin')}</h1>
          <p className="text-text-secondary text-sm mt-2 text-center">
            {t('enterPinDescription')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            inputMode="numeric"
            autoFocus
            maxLength={MAX_PIN_LENGTH}
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            placeholder="••••"
            className="w-full px-4 py-3 bg-card border border-border rounded-lg text-center text-2xl tracking-[0.5em] focus:outline-none focus:border-gold"
            disabled={isUnlocking}
          />

          {error !== null && (
            <p className="text-red text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={pin.length < 4 || isUnlocking}
            className="w-full bg-gold text-background py-3 rounded-lg font-semibold disabled:opacity-50"
          >
            {isUnlocking ? t('loading') : t('unlock')}
          </button>
        </form>
      </div>
    </div>
  );
}
