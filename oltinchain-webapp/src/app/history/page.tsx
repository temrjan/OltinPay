"use client"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { walletApi } from "@/lib/api"
import { useAuthStore } from "@/lib/store"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

function formatNumber(n: number, decimals = 2) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

const typeLabels: Record<string, string> = {
  buy: "Покупка",
  sell: "Продажа",
  transfer_in: "Получено",
  transfer_out: "Отправлено",
  deposit: "Пополнение",
  bonus: "Бонус",
}

const typeColors: Record<string, string> = {
  buy: "text-gold",
  sell: "text-red-400",
  transfer_in: "text-green-500",
  transfer_out: "text-orange-400",
  deposit: "text-green-500",
  bonus: "text-gold",
}

export default function HistoryPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const [transactions, setTransactions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/auth/login")
      return
    }

    const fetchHistory = async () => {
      try {
        const { data } = await walletApi.getTransactions(100)
        setTransactions(data.transactions || data.items || data || [])
      } catch (err: any) {
        console.error(err)
        setError("Ошибка загрузки")
      } finally {
        setLoading(false)
      }
    }

    fetchHistory()
  }, [isAuthenticated, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-gold">Загрузка...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4">
      <header className="flex items-center mb-6">
        <button onClick={() => router.push("/dashboard")} className="text-muted mr-4 text-xl">←</button>
        <h1 className="text-xl font-bold">История</h1>
      </header>

      {error && (
        <Card className="p-4 mb-4 text-center">
          <p className="text-red-500">{error}</p>
          <Button onClick={() => router.push("/dashboard")} className="mt-4">
            На главную
          </Button>
        </Card>
      )}

      {!error && transactions.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-muted mb-4">Нет транзакций</p>
          <p className="text-sm text-muted mb-4">Совершите первую покупку OLTIN!</p>
          <Button onClick={() => router.push("/buy")}>
            Купить OLTIN
          </Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {transactions.map((tx, idx) => (
            <Card key={tx.id || idx} className="p-3">
              <div className="flex justify-between items-start">
                <div>
                  <p className={`font-medium ${typeColors[tx.type] || "text-white"}`}>
                    {typeLabels[tx.type] || tx.type}
                  </p>
                  <p className="text-xs text-muted">{formatDate(tx.created_at)}</p>
                </div>
                <div className="text-right">
                  {tx.amount_oltin && (
                    <p className="font-mono">
                      {tx.type === "sell" || tx.type === "transfer_out" ? "-" : "+"}
                      {formatNumber(parseFloat(tx.amount_oltin), 4)} OLTIN
                    </p>
                  )}
                  {tx.amount_uzs && (
                    <p className="text-sm text-muted">
                      {formatNumber(parseFloat(tx.amount_uzs), 0)} UZS
                    </p>
                  )}
                </div>
              </div>
              {tx.tx_hash && (
                <a
                  href={`https://sepolia.explorer.zksync.io/tx/${tx.tx_hash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-gold hover:underline mt-2 block"
                >
                  {tx.tx_hash.slice(0, 10)}...{tx.tx_hash.slice(-8)} →
                </a>
              )}
              {tx.to_address && (
                <p className="text-xs text-muted mt-1 font-mono truncate">
                  → {tx.to_address}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
