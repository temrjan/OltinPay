import { create } from 'zustand';

interface AppState {
  // Auth
  token: string | null;
  isAuthenticated: boolean;

  // Language
  language: string | null;

  // Actions
  setToken: (token: string | null) => void;
  setLanguage: (lang: string) => void;
  logout: () => void;
  initFromStorage: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  token: null,
  isAuthenticated: false,
  language: null,

  // Actions
  setToken: (token) => set({
    token,
    isAuthenticated: !!token
  }),

  setLanguage: (language) => set({ language }),

  logout: () => set({
    token: null,
    isAuthenticated: false
  }),

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
