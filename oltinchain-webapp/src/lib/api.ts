import axios, { AxiosError, InternalAxiosRequestConfig } from "axios"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.oltinchain.com"

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

// Track if we are currently refreshing
let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: Error) => void
}> = []

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else if (token) {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window \!== "undefined") {
    const token = localStorage.getItem("access_token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Handle 401 errors with token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    if (error.response?.status === 401 && \!originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return api(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = localStorage.getItem("refresh_token")
        if (\!refreshToken) {
          throw new Error("No refresh token")
        }

        const { data } = await axios.post(`${API_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })

        const newAccessToken = data.access_token
        localStorage.setItem("access_token", newAccessToken)
        if (data.refresh_token) {
          localStorage.setItem("refresh_token", data.refresh_token)
        }

        processQueue(null, newAccessToken)
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError as Error, null)
        localStorage.removeItem("access_token")
        localStorage.removeItem("refresh_token")
        if (typeof window \!== "undefined") {
          window.location.href = "/auth/login"
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// Auth
export const authApi = {
  register: (phone: string, password: string) =>
    api.post("/auth/register", { phone, password }),
  login: (phone: string, password: string) =>
    api.post("/auth/login", { phone, password }),
  refresh: (refreshToken: string) =>
    api.post("/auth/refresh", { refresh_token: refreshToken }),
}

// Wallet
export const walletApi = {
  getBalance: () => api.get("/wallet/balance"),
  getTransactions: (limit = 50, offset = 0) =>
    api.get(`/wallet/transactions?limit=${limit}&offset=${offset}`),
  transfer: (toAddress: string, amount: number) =>
    api.post("/wallet/transfer", { to_address: toAddress, amount }),
  deposit: (amountUzs: number) =>
    api.post("/wallet/deposit", { amount_uzs: amountUzs }),
}

// Price
export const priceApi = {
  getGoldPrice: () => api.get("/price/gold"),
  getBuyQuote: (amountUzs: number) =>
    api.post("/price/quote/buy", { amount_uzs: amountUzs }),
  getSellQuote: (amountOltin: number) =>
    api.post("/price/quote/sell", { amount_oltin: amountOltin }),
}

// Orders
export const ordersApi = {
  buy: (amountUzs: number) => api.post("/orders/buy", { amount_uzs: amountUzs }),
  sell: (amountOltin: number) =>
    api.post("/orders/sell", { amount_oltin: amountOltin }),
  getHistory: (limit = 50, offset = 0) =>
    api.get(`/orders?limit=${limit}&offset=${offset}`),
}

// User
export const userApi = {
  getMe: () => api.get("/users/me"),
}
