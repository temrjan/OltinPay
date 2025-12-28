import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.oltinchain.com'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Auth
export const authApi = {
  register: (phone: string, password: string) =>
    api.post('/auth/register', { phone, password }),
  login: (phone: string, password: string) =>
    api.post('/auth/login', { phone, password }),
  refresh: (refreshToken: string) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),
}

// Wallet
export const walletApi = {
  getBalance: () => api.get('/wallet/balance'),
  getTransactions: (limit = 50, offset = 0) =>
    api.get(`/wallet/transactions?limit=${limit}&offset=${offset}`),
  transfer: (toAddress: string, amount: number) =>
    api.post('/wallet/transfer', { to_address: toAddress, amount }),
  deposit: (amountUzs: number) =>
    api.post('/wallet/deposit', { amount_uzs: amountUzs }),
}

// Price
export const priceApi = {
  getGoldPrice: () => api.get('/price/gold'),
  getBuyQuote: (amountUzs: number) =>
    api.post('/price/quote/buy', { amount_uzs: amountUzs }),
  getSellQuote: (amountOltin: number) =>
    api.post('/price/quote/sell', { amount_oltin: amountOltin }),
}

// Orders
export const ordersApi = {
  buy: (amountUzs: number) =>
    api.post('/orders/buy', { amount_uzs: amountUzs }),
  sell: (amountOltin: number) =>
    api.post('/orders/sell', { amount_oltin: amountOltin }),
  getHistory: (limit = 50, offset = 0) =>
    api.get(`/orders?limit=${limit}&offset=${offset}`),
}

// User
export const userApi = {
  getMe: () => api.get('/users/me'),
}
