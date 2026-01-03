"use client"
import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import axios from "axios"
import { priceApi, ordersApi, walletApi } from "@/lib/api"
import { useAuthStore, useWalletStore } from "@/lib/store"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { BuyQuote } from "@/lib/types"

function formatNumber(n: number, decimals = 2) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

export default function BuyPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const { balance, setBalance } = useWalletStore()
  const [amount, setAmount] = useState("")
  const [quote, setQuote] = useState<BuyQuote | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/auth/login")
    }
  }, [isAuthenticated, router])

  useEffect(() => {
    const getQuote = async () => {
      const amountNum = parseFloat(amount)
      if (!amountNum || amountNum <= 0) {
        setQuote(null)
        return
      }
      try {
        const { data } = await priceApi.getBuyQuote(amountNum)
        setQuote(data)
        setError("")
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) {
          setError(err.response?.data?.detail || "Ошибка расчёта")
        } else {
          setError("Ошибка расчёта")
        }
        setQuote(null)
      }
    }

    const timer = setTimeout(getQuote, 300)
    return () => clearTimeout(timer)
  }, [amount])

  const handleBuy = useCallback(async () => {
    const amountNum = parseFloat(amount)
    if (!amountNum || !quote) return

    setLoading(true)
    setError("")

    try {
      await ordersApi.buy(amountNum)
      setSuccess(true)
      const { data } = await walletApi.getBalance()
      setBalance(data)
      setTimeout(() => router.push("/dashboard"), 1500)
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || "Ошибка покупки")
      } else {
        setError("Ошибка покупки")
      }
    } finally {
      setLoading(false)
    }
  }, [amount, quote, router, setBalance])

  const setPreset = useCallback((percent: number) => {
    if (balance?.usd.available) {
      setAmount(Math.floor(balance.usd.available * percent / 100).toString())
    }
  }, [balance?.usd.available])

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Card className="p-6 text-center">
          <div className="text-4xl mb-4">✓</div>
          <h2 className="text-xl font-bold text-gold">Покупка успешна!</h2>
          <p className="text-muted mt-2">+{formatNumber(quote?.amount_oltin || 0, 4)} OLTIN</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4">
      <header className="flex items-center mb-6">
        <Link href="/dashboard" className="text-muted mr-4">←</Link>
        <h1 className="text-xl font-bold">Купить OLTIN</h1>
      </header>

      <Card className="p-4 mb-4">
        <p className="text-muted text-sm mb-2">
          Доступно: {formatNumber(balance?.usd.available || 0, 0)} USD
        </p>

        <div className="mb-4">
          <label className="text-sm text-muted">Сумма в USD</label>
          <Input
            type="number"
            placeholder="100000"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>

        <div className="flex gap-2 mb-4">
          {[25, 50, 75, 100].map((p) => (
            <button
              key={p}
              onClick={() => setPreset(p)}
              className="flex-1 py-1 text-sm bg-background rounded border border-border"
            >
              {p}%
            </button>
          ))}
        </div>

        {quote && (
          <div className="bg-background p-3 rounded space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted">Вы платите</span>
              <span>{formatNumber(quote.amount_uzs, 0)} USD</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted">Комиссия</span>
              <span>{formatNumber(quote.fee_uzs, 0)} USD</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted">Цена за грамм</span>
              <span>{formatNumber(quote.price_per_gram, 0)} USD</span>
            </div>
            <div className="flex justify-between font-bold border-t border-border pt-2">
              <span>Получите</span>
              <span className="text-gold">{formatNumber(quote.amount_oltin, 4)} OLTIN</span>
            </div>
          </div>
        )}

        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </Card>

      <Button
        onClick={handleBuy}
        disabled={!quote || loading}
        className="w-full bg-green-600 hover:bg-green-700"
      >
        {loading ? "Обработка..." : "Купить OLTIN"}
      </Button>
    </div>
  )
}
