import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  phone: string
  wallet_address: string | null
}

interface Balance {
  uzs: { available: number; locked: number; total: number }
  oltin: { available: number; locked: number; total: number }
  wallet_address: string | null
}

interface Price {
  base_price: number
  buy_price: number
  sell_price: number
  spread_percent: number
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setAuth: (user: User, accessToken: string, refreshToken: string) => void
  logout: () => void
}

interface WalletState {
  balance: Balance | null
  setBalance: (balance: Balance) => void
}

interface PriceState {
  price: Price | null
  setPrice: (price: Price) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setAuth: (user, accessToken, refreshToken) =>
        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
        }),
      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
)

export const useWalletStore = create<WalletState>((set) => ({
  balance: null,
  setBalance: (balance) => set({ balance }),
}))

export const usePriceStore = create<PriceState>((set) => ({
  price: null,
  setPrice: (price) => set({ price }),
}))
