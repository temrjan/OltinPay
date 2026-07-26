/**
 * In-memory wallet session store. Holds the unlocked HD account and the
 * timestamp of the last user action; auto-locks after IDLE_TIMEOUT_MS.
 *
 * The seed is NEVER persisted unencrypted — only kept here for the
 * duration of the session.
 */

import {create} from 'zustand';
import type {HDAccount} from 'viem/accounts';

const IDLE_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

interface WalletState {
  account: HDAccount | null;
  unlockedAt: number | null;
  // Whether an encrypted wallet exists in storage. null = not yet checked.
  // Lives here (not in a WalletGate-local one-shot effect) so onboarding/restore
  // can flip it synchronously and the gate reacts without a stale snapshot.
  hasWallet: boolean | null;
  unlock: (account: HDAccount) => void;
  lock: () => void;
  touch: () => void;
  isExpired: () => boolean;
  setHasWallet: (present: boolean) => void;
}

export const useWalletStore = create<WalletState>((set, get) => ({
  account: null,
  unlockedAt: null,
  hasWallet: null,

  // Unlocking always implies a wallet exists in storage, so record presence
  // here. This is what lets WalletGate see the wallet the moment onboarding/
  // restore finishes (they call unlock before router.push), instead of the
  // stale one-shot check that bounced every new user back to /onboarding.
  unlock: (account) => set({account, unlockedAt: Date.now(), hasWallet: true}),

  // Lock clears the in-memory session only — the encrypted wallet still exists,
  // so hasWallet stays true (gate shows PinUnlock, not onboarding).
  lock: () => set({account: null, unlockedAt: null}),

  touch: () => set({unlockedAt: Date.now()}),

  isExpired: () => {
    const ts = get().unlockedAt;
    if (ts === null) return true;
    return Date.now() - ts > IDLE_TIMEOUT_MS;
  },

  setHasWallet: (present) => set({hasWallet: present}),
}));
