"use client"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { priceApi, ordersApi, walletApi } from "@/lib/api"
import { useAuthStore, useWalletStore } from "@/lib/store"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

function formatNumber(n: number, decimals = 2) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

export default function SellPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const { balance, setBalance } = useWalletStore()
  const [amount, setAmount] = useState("")
  const [quote, setQuote] = useState<any>(null)
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
        const { data } = await priceApi.getSellQuote(amountNum)
        setQuote(data)
        setError("")
      } catch (err: any) {
        setError(err.response?.data?.detail || "Ошибка расчёта")
        setQuote(null)
      }
    }

    const timer = setTimeout(getQuote, 300)
    return () => clearTimeout(timer)
  }, [amount])

  const handleSell = async () => {
    const amountNum = parseFloat(amount)
    if (!amountNum || !quote) return

    setLoading(true)
    setError("")

    try {
      await ordersApi.sell(amountNum)
      setSuccess(true)
      const { data } = await walletApi.getBalance()
      setBalance(data)
      setTimeout(() => router.push("/dashboard"), 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Ошибка продажи")
    } finally {
      setLoading(false)
    }
  }

  const setPreset = (percent: number) => {
    if (balance?.oltin.available) {
      const val = balance.oltin.available * percent / 100
      setAmount(val.toFixed(4))
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Card className="p-6 text-center">
          <div className="text-4xl mb-4">✓</div>
          <h2 className="text-xl font-bold text-gold">Продажа успешна!</h2>
          <p className="text-muted mt-2">+{formatNumber(quote?.amount_usd || 0, 0)} USD</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4">
      <header className="flex items-center mb-6">
        <Link href="/dashboard" className="text-muted mr-4">←</Link>
        <h1 className="text-xl font-bold">Продать OLTIN</h1>
      </header>

      <Card className="p-4 mb-4">
        <p className="text-muted text-sm mb-2">
          Доступно: {formatNumber(balance?.oltin.available || 0, 4)} OLTIN
        </p>

        <div className="mb-4">
          <label className="text-sm text-muted">Количество OLTIN (граммы)</label>
          <Input
            type="number"
            step="0.0001"
            placeholder="0.5"
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
              <span className="text-muted">Продаёте</span>
              <span>{formatNumber(quote.amount_oltin, 4)} OLTIN</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted">Комиссия</span>
              <span>{formatNumber(quote.fee_usd, 0)} USD</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted">Цена за грамм</span>
              <span>{formatNumber(quote.price_per_gram, 0)} USD</span>
            </div>
            <div className="flex justify-between font-bold border-t border-border pt-2">
              <span>Получите</span>
              <span className="text-green-500">{formatNumber(quote.amount_usd, 0)} USD</span>
            </div>
          </div>
        )}

        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </Card>

      <Button
        onClick={handleSell}
        disabled={!quote || loading}
        className="w-full bg-red-500 hover:bg-red-600"
      >
        {loading ? "Обработка..." : "Продать OLTIN"}
      </Button>
    </div>
  )
}
