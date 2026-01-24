"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import {
  isTelegramWebApp,
  getInitData,
  initTelegramWebApp,
  hapticFeedback,
} from "@/lib/telegram"
import { authApi, userApi } from "@/lib/api"
import { useAuthStore } from "@/lib/store"

interface TelegramAuthProviderProps {
  children: React.ReactNode
}

export function TelegramAuthProvider({ children }: TelegramAuthProviderProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { setAuth, isAuthenticated } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    const initAuth = async () => {
      // Initialize Telegram WebApp
      initTelegramWebApp()

      // Check if already authenticated
      const token = localStorage.getItem("access_token")
      if (token) {
        setIsLoading(false)
        return
      }

      // Check if we are in Telegram Mini App
      if (!isTelegramWebApp()) {
        setIsLoading(false)
        return
      }

      // Get initData for backend validation
      const initData = getInitData()
      if (!initData) {
        setIsLoading(false)
        return
      }

      try {
        // Authenticate via Telegram
        const { data } = await authApi.telegram(initData)

        // Save tokens
        localStorage.setItem("access_token", data.access_token)
        localStorage.setItem("refresh_token", data.refresh_token)

        // Get user profile
        const userRes = await userApi.getMe()

        // Update auth store
        setAuth(
          {
            id: userRes.data.id,
            phone: userRes.data.phone,
            wallet_address: userRes.data.wallet_address,
            telegram_username: data.telegram_username,
          },
          data.access_token,
          data.refresh_token
        )

        // Haptic feedback on success
        hapticFeedback("success")

        // Redirect to dashboard
        router.push("/dashboard")
      } catch (err: any) {
        console.error("Telegram auth failed:", err)
        setError(err.response?.data?.detail || "Authentication failed")
        hapticFeedback("error")
      } finally {
        setIsLoading(false)
      }
    }

    initAuth()
  }, [router, setAuth])

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background">
        <div className="w-12 h-12 border-4 border-gold border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-muted animate-pulse">Загрузка...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4">
        <div className="text-4xl mb-4">⚠️</div>
        <p className="text-red-500 text-center mb-4">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-gold text-black rounded font-medium"
        >
          Попробовать снова
        </button>
      </div>
    )
  }

  return <>{children}</>
}
