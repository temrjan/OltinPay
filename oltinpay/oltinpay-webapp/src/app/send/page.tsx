'use client';

import { useState } from 'react';
import { ArrowLeft, Search, User } from 'lucide-react';
import Link from 'next/link';
import { useTelegram } from '@/hooks/useTelegram';

export default function SendPage() {
  const { hapticFeedback } = useTelegram();
  const [step, setStep] = useState<'recipient' | 'amount' | 'confirm'>('recipient');
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');

  const balance = 0; // Mock balance

  return (
    <div className="flex flex-col h-[calc(100vh-60px)]">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-border">
        <Link href="/wallet" className="text-text-muted">
          <ArrowLeft size={24} />
        </Link>
        <h1 className="text-lg font-semibold">OLTIN yuborish</h1>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-4">
        {step === 'recipient' && (
          <>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted" size={20} />
              <input
                type="text"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder="@username yoki OltinPay ID"
                className="w-full bg-card border border-border rounded-xl pl-12 pr-4 py-3 focus:outline-none focus:border-gold"
              />
            </div>

            {recipient && (
              <button
                onClick={() => { setStep('amount'); hapticFeedback('selection'); }}
                className="w-full bg-card border border-border rounded-xl p-4 flex items-center gap-3"
              >
                <div className="w-10 h-10 rounded-full bg-gold/20 flex items-center justify-center">
                  <User className="text-gold" size={20} />
                </div>
                <span>@{recipient}</span>
              </button>
            )}
          </>
        )}

        {step === 'amount' && (
          <>
            <div className="text-center text-text-muted text-sm mb-2">
              Qabul qiluvchi: @{recipient}
            </div>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.0000"
              className="w-full bg-background border border-border rounded-xl px-4 py-3 text-2xl text-center focus:outline-none focus:border-gold"
            />
            <div className="text-center text-text-muted text-sm">
              Mavjud: {balance.toFixed(4)} OLTIN
            </div>
            <button
              onClick={() => { setStep('confirm'); hapticFeedback('medium'); }}
              disabled={!amount || parseFloat(amount) <= 0}
              className="w-full bg-gold text-background py-4 rounded-xl font-semibold disabled:opacity-50"
            >
              Davom etish
            </button>
          </>
        )}

        {step === 'confirm' && (
          <div className="space-y-4">
            <div className="bg-card rounded-xl p-4 space-y-3">
              <div className="flex justify-between">
                <span className="text-text-muted">Qabul qiluvchi</span>
                <span>@{recipient}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Miqdor</span>
                <span className="text-gold font-semibold">{amount} OLTIN</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Komissiya (1%)</span>
                <span>{(parseFloat(amount) * 0.01).toFixed(6)} OLTIN</span>
              </div>
            </div>
            <button
              onClick={() => hapticFeedback('success')}
              className="w-full bg-gold text-background py-4 rounded-xl font-semibold"
            >
              Tasdiqlash
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
