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
  unlock: (account: HDAccount) => void;
  lock: () => void;
  touch: () => void;
  isExpired: () => boolean;
}

export const useWalletStore = create<WalletState>((set, get) => ({
  account: null,
  unlockedAt: null,

  unlock: (account) => set({account, unlockedAt: Date.now()}),

  lock: () => set({account: null, unlockedAt: null}),

  touch: () => set({unlockedAt: Date.now()}),

  isExpired: () => {
    const ts = get().unlockedAt;
    if (ts === null) return true;
    return Date.now() - ts > IDLE_TIMEOUT_MS;
  },
}));
