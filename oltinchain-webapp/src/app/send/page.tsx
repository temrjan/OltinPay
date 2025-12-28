"use client"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { walletApi } from "@/lib/api"
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

export default function SendPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const { balance, setBalance } = useWalletStore()
  const [address, setAddress] = useState("")
  const [amount, setAmount] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [txHash, setTxHash] = useState("")

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/auth/login")
    }
  }, [isAuthenticated, router])

  const isValidAddress = (addr: string) => /^0x[a-fA-F0-9]{40}$/.test(addr)

  const handleSend = async () => {
    const amountNum = parseFloat(amount)
    if (!amountNum || !isValidAddress(address)) return

    if (amountNum > (balance?.oltin.available || 0)) {
      setError("Недостаточно OLTIN")
      return
    }

    setLoading(true)
    setError("")

    try {
      const { data } = await walletApi.transfer(address, amountNum)
      setTxHash(data.tx_hash)
      setSuccess(true)
      const balanceRes = await walletApi.getBalance()
      setBalance(balanceRes.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Ошибка перевода")
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
          <h2 className="text-xl font-bold text-gold">Перевод отправлен!</h2>
          <p className="text-muted mt-2">{formatNumber(parseFloat(amount), 4)} OLTIN</p>
          {txHash && (
            <a
              href={`https://sepolia.explorer.zksync.io/tx/${txHash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-gold underline mt-4 block"
            >
              Посмотреть в Explorer →
            </a>
          )}
          <Button
            onClick={() => router.push("/dashboard")}
            className="mt-4"
          >
            На главную
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4">
      <header className="flex items-center mb-6">
        <Link href="/dashboard" className="text-muted mr-4">←</Link>
        <h1 className="text-xl font-bold">Отправить OLTIN</h1>
      </header>

      <Card className="p-4 mb-4">
        <p className="text-muted text-sm mb-4">
          Доступно: {formatNumber(balance?.oltin.available || 0, 4)} OLTIN
        </p>
        
        <div className="mb-4">
          <label className="text-sm text-muted">Адрес получателя</label>
          <Input
            type="text"
            placeholder="0x..."
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
          {address && !isValidAddress(address) && (
            <p className="text-red-500 text-xs mt-1">Неверный формат адреса</p>
          )}
        </div>

        <div className="mb-4">
          <label className="text-sm text-muted">Количество OLTIN</label>
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

        <div className="bg-background p-3 rounded text-sm text-muted">
          <p>⚠️ Переводы OLTIN происходят в блокчейне zkSync Era.</p>
          <p className="mt-1">Убедитесь в правильности адреса!</p>
        </div>

        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </Card>

      <Button
        onClick={handleSend}
        disabled={!isValidAddress(address) || !parseFloat(amount) || loading}
        className="w-full"
      >
        {loading ? "Отправка..." : "Отправить OLTIN"}
      </Button>
    </div>
  )
}
