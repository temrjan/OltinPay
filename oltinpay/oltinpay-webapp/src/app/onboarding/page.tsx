'use client';

import {useMemo, useState} from 'react';
import {useRouter} from 'next/navigation';
import Link from 'next/link';
import {ArrowRight, Check, Eye, EyeOff, ShieldAlert} from 'lucide-react';

import {useTranslation} from '@/hooks/useTranslation';
import {useWalletStore} from '@/stores/wallet';
import {DemoBadge} from '@/components/DemoBadge';
import {
  encryptMnemonic,
  mnemonicToHDAccount,
  newMnemonic,
  saveEncryptedWallet,
} from '@/lib/wallet';

type Step = 'welcome' | 'show' | 'verify' | 'pin';

const VERIFY_INDICES = [2, 6, 10] as const; // 0-based, so words 3, 7, 11

export default function OnboardingPage() {
  const router = useRouter();
  const {t} = useTranslation();
  const unlock = useWalletStore((s) => s.unlock);

  const [step, setStep] = useState<Step>('welcome');
  const [mnemonic, setMnemonic] = useState<string>('');
  const [revealed, setRevealed] = useState(false);
  const [verifyInputs, setVerifyInputs] = useState<Record<number, string>>({});
  const [pin, setPin] = useState('');
  const [pinConfirm, setPinConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const words = useMemo(() => mnemonic.split(' '), [mnemonic]);

  const handleStart = () => {
    setMnemonic(newMnemonic());
    setStep('show');
  };

  const handleAfterShow = () => {
    setVerifyInputs({});
    setStep('verify');
  };

  const verifyInputsValid = useMemo(() => {
    return VERIFY_INDICES.every(
      (idx) => (verifyInputs[idx] ?? '').trim().toLowerCase() === words[idx],
    );
  }, [verifyInputs, words]);

  const handleVerify = () => {
    if (!verifyInputsValid) {
      setError(t('seedVerifyError'));
      return;
    }
    setError(null);
    setStep('pin');
  };

  const handleFinish = async () => {
    setError(null);
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
      const blob = await encryptMnemonic(mnemonic, pin);
      await saveEncryptedWallet(blob);
      const account = mnemonicToHDAccount(mnemonic);
      unlock(account);
      router.push('/wallet');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save wallet');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 pb-24">
      <div className="max-w-md mx-auto space-y-6">
        <DemoBadge />

        {step === 'welcome' && <WelcomeStep onNext={handleStart} />}

        {step === 'show' && (
          <ShowSeedStep
            words={words}
            revealed={revealed}
            onToggle={() => setRevealed((v) => !v)}
            onNext={handleAfterShow}
          />
        )}

        {step === 'verify' && (
          <VerifyStep
            indices={VERIFY_INDICES}
            inputs={verifyInputs}
            onChange={(idx, value) =>
              setVerifyInputs((prev) => ({...prev, [idx]: value}))
            }
            error={error}
            onNext={handleVerify}
            valid={verifyInputsValid}
          />
        )}

        {step === 'pin' && (
          <PinStep
            pin={pin}
            pinConfirm={pinConfirm}
            error={error}
            isSaving={isSaving}
            onPinChange={setPin}
            onPinConfirmChange={setPinConfirm}
            onFinish={handleFinish}
          />
        )}

        <div className="text-center text-text-secondary text-sm">
          <Link href="/onboarding/restore" className="underline">
            {t('restoreFromSeed')}
          </Link>
        </div>
      </div>
    </div>
  );
}

// ─── Step 1 ──────────────────────────────────────────────────────────

function WelcomeStep({onNext}: {onNext: () => void}) {
  const {t} = useTranslation();
  return (
    <>
      <h1 className="text-3xl font-bold text-text-primary">{t('onboardWelcome')}</h1>
      <p className="text-text-secondary leading-relaxed">{t('onboardWelcomeDescription')}</p>
      <ul className="space-y-2 text-sm text-text-secondary">
        <li>• {t('onboardWelcomeBullet1')}</li>
        <li>• {t('onboardWelcomeBullet2')}</li>
        <li>• {t('onboardWelcomeBullet3')}</li>
      </ul>
      <button
        onClick={onNext}
        className="w-full bg-gold text-background py-3 rounded-lg font-semibold flex items-center justify-center gap-2"
      >
        {t('createWallet')}
        <ArrowRight className="w-4 h-4" />
      </button>
    </>
  );
}

// ─── Step 2 ──────────────────────────────────────────────────────────

interface ShowSeedStepProps {
  words: string[];
  revealed: boolean;
  onToggle: () => void;
  onNext: () => void;
}

function ShowSeedStep({words, revealed, onToggle, onNext}: ShowSeedStepProps) {
  const {t} = useTranslation();
  return (
    <>
      <h1 className="text-2xl font-bold text-text-primary">{t('seedTitle')}</h1>
      <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 flex gap-3">
        <ShieldAlert className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
        <p className="text-yellow-100 text-sm leading-relaxed">{t('seedWarning')}</p>
      </div>

      <div className="bg-card border border-border rounded-lg p-4 relative">
        <button
          onClick={onToggle}
          className="absolute top-3 right-3 text-text-secondary"
          aria-label={revealed ? t('hide') : t('reveal')}
        >
          {revealed ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
        </button>
        <ol className="grid grid-cols-2 gap-x-4 gap-y-2 mt-2">
          {words.map((word, i) => (
            <li key={i} className="flex gap-2 text-text-primary">
              <span className="text-text-secondary w-6 text-right">{i + 1}.</span>
              <span className="font-mono">{revealed ? word : '••••'}</span>
            </li>
          ))}
        </ol>
      </div>

      <button
        onClick={onNext}
        disabled={!revealed}
        className="w-full bg-gold text-background py-3 rounded-lg font-semibold disabled:opacity-50"
      >
        {t('seedWrittenDown')}
      </button>
    </>
  );
}

// ─── Step 3 ──────────────────────────────────────────────────────────

interface VerifyStepProps {
  indices: readonly number[];
  inputs: Record<number, string>;
  error: string | null;
  valid: boolean;
  onChange: (idx: number, value: string) => void;
  onNext: () => void;
}

function VerifyStep({indices, inputs, error, valid, onChange, onNext}: VerifyStepProps) {
  const {t} = useTranslation();
  return (
    <>
      <h1 className="text-2xl font-bold text-text-primary">{t('verifyTitle')}</h1>
      <p className="text-text-secondary text-sm">{t('verifyDescription')}</p>

      <div className="space-y-3">
        {indices.map((idx) => (
          <div key={idx}>
            <label className="block text-text-secondary text-sm mb-1">
              {t('wordNumber')} {idx + 1}
            </label>
            <input
              type="text"
              autoCapitalize="none"
              autoComplete="off"
              value={inputs[idx] ?? ''}
              onChange={(e) => onChange(idx, e.target.value)}
              className="w-full px-4 py-2 bg-card border border-border rounded-lg focus:outline-none focus:border-gold"
            />
          </div>
        ))}
      </div>

      {error !== null && <p className="text-red text-sm">{error}</p>}

      <button
        onClick={onNext}
        disabled={!valid}
        className="w-full bg-gold text-background py-3 rounded-lg font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {valid && <Check className="w-4 h-4" />}
        {t('next')}
      </button>
    </>
  );
}

// ─── Step 4 ──────────────────────────────────────────────────────────

interface PinStepProps {
  pin: string;
  pinConfirm: string;
  error: string | null;
  isSaving: boolean;
  onPinChange: (v: string) => void;
  onPinConfirmChange: (v: string) => void;
  onFinish: () => void;
}

function PinStep({
  pin,
  pinConfirm,
  error,
  isSaving,
  onPinChange,
  onPinConfirmChange,
  onFinish,
}: PinStepProps) {
  const {t} = useTranslation();
  return (
    <>
      <h1 className="text-2xl font-bold text-text-primary">{t('pinTitle')}</h1>
      <p className="text-text-secondary text-sm">{t('pinDescription')}</p>

      <div className="space-y-3">
        <input
          type="password"
          inputMode="numeric"
          maxLength={12}
          value={pin}
          onChange={(e) => onPinChange(e.target.value)}
          placeholder={t('pin')}
          className="w-full px-4 py-3 bg-card border border-border rounded-lg text-center text-2xl tracking-[0.5em] focus:outline-none focus:border-gold"
        />
        <input
          type="password"
          inputMode="numeric"
          maxLength={12}
          value={pinConfirm}
          onChange={(e) => onPinConfirmChange(e.target.value)}
          placeholder={t('pinConfirm')}
          className="w-full px-4 py-3 bg-card border border-border rounded-lg text-center text-2xl tracking-[0.5em] focus:outline-none focus:border-gold"
        />
      </div>

      {error !== null && <p className="text-red text-sm">{error}</p>}

      <button
        onClick={onFinish}
        disabled={pin.length < 4 || pin !== pinConfirm || isSaving}
        className="w-full bg-gold text-background py-3 rounded-lg font-semibold disabled:opacity-50"
      >
        {isSaving ? t('loading') : t('finish')}
      </button>
    </>
  );
}
