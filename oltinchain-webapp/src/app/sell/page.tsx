"use client"
import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import axios from "axios"
import { priceApi, ordersApi, walletApi } from "@/lib/api"
import { useWalletStore } from "@/lib/store"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { SellQuote } from "@/lib/types"

function formatNumber(n: number, decimals = 2) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

export default function SellPage() {
  const router = useRouter()
  const { balance, setBalance } = useWalletStore()
  const [amount, setAmount] = useState("")
  const [quote, setQuote] = useState<SellQuote | null>(null)
  const [loading, setLoading] = useState(false)
  const [quoteLoading, setQuoteLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)

  // Fetch balance on mount
  useEffect(() => {
    const fetchBalance = async () => {
      try {
        const { data } = await walletApi.getBalance()
        setBalance(data)
      } catch (err) {
        console.error("Failed to fetch balance", err)
      }
    }
    if (!balance) {
      fetchBalance()
    }
  }, [balance, setBalance])

  useEffect(() => {
    const getQuote = async () => {
      const amountNum = parseFloat(amount)
      if (!amountNum || amountNum <= 0) {
        setQuote(null)
        return
      }

      setQuoteLoading(true)
      try {
        const { data } = await priceApi.getSellQuote(amountNum)
        setQuote(data)
        setError("")
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) {
          setError(err.response?.data?.detail || "Ошибка расчёта")
        } else {
          setError("Ошибка расчёта")
        }
        setQuote(null)
      } finally {
        setQuoteLoading(false)
      }
    }

    const timer = setTimeout(getQuote, 300)
    return () => clearTimeout(timer)
  }, [amount])

  const handleSell = useCallback(async () => {
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
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || "Ошибка продажи")
      } else {
        setError("Ошибка продажи")
      }
    } finally {
      setLoading(false)
    }
  }, [amount, quote, router, setBalance])

  const setPreset = useCallback((percent: number) => {
    if (balance?.oltin.available) {
      const val = balance.oltin.available * percent / 100
      setAmount(val.toFixed(4))
    }
  }, [balance?.oltin.available])

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

  const canSell = quote && !loading && !quoteLoading && parseFloat(amount) > 0

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

        {quoteLoading && (
          <div className="bg-background p-3 rounded text-center text-muted">
            Расчёт...
          </div>
        )}

        {quote && !quoteLoading && (
          <div className="bg-background p-3 rounded space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted">Продаёте</span>
              <span>{formatNumber(quote.amount_oltin, 4)} OLTIN</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted">Комиссия</span>
              <span>{formatNumber(quote.fee_usd, 2)} USD</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted">Цена за грамм</span>
              <span>{formatNumber(quote.price_per_gram, 2)} USD</span>
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
        disabled={!canSell}
        className="w-full bg-red-500 hover:bg-red-600 disabled:opacity-50"
      >
        {loading ? "Обработка..." : quoteLoading ? "Расчёт..." : "Продать OLTIN"}
      </Button>
    </div>
  )
}
