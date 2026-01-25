import { create } from 'zustand';

interface User {
  id: string;
  telegram_id: number;
  oltin_id: string;
  language: string;
  created_at: string;
}

// Sync initialization from localStorage
const getInitialState = () => {
  if (typeof window === 'undefined') {
    return { token: null, language: null };
  }
  const token = localStorage.getItem('oltinpay_token');
  const language = localStorage.getItem('oltinpay_lang');
  return { token, language };
};

interface AppState {
  // Auth
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;

  // Language
  language: string | null;

  // Actions
  setToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  setLanguage: (lang: string) => void;
  logout: () => void;
  initFromStorage: () => void;
}

const initialState = typeof window !== 'undefined' ? getInitialState() : { token: null, language: null };

export const useAppStore = create<AppState>((set) => ({
  // Initial state - sync from localStorage
  token: initialState.token,
  user: null,
  isAuthenticated: !!initialState.token,
  language: initialState.language,

  // Actions
  setToken: (token) => set({
    token,
    isAuthenticated: !!token
  }),

  setUser: (user) => set({ user }),

  setLanguage: (language) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('oltinpay_lang', language);
    }
    set({ language });
  },

  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('oltinpay_token');
      localStorage.removeItem('oltinpay_lang');
    }
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      language: null,
    });
  },

  initFromStorage: () => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('oltinpay_token');
      const language = localStorage.getItem('oltinpay_lang');
      set({
        token,
        isAuthenticated: !!token,
        language,
      });
    }
  },
}));
