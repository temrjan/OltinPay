"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { walletApi, userApi } from "@/lib/api"
import { useWalletStore } from "@/lib/store"
import { hapticFeedback } from "@/lib/telegram"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

type TransferMode = "username" | "address"

interface FoundUser {
  id: string
  username: string | null
  first_name: string | null
  has_wallet: boolean
}

function formatNumber(n: number, decimals = 2) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

export default function SendPage() {
  const router = useRouter()
  const { balance, setBalance } = useWalletStore()

  const [mode, setMode] = useState<TransferMode>("username")
  const [recipient, setRecipient] = useState("")
  const [amount, setAmount] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [txHash, setTxHash] = useState("")

  // Username search state
  const [foundUser, setFoundUser] = useState<FoundUser | null>(null)
  const [searching, setSearching] = useState(false)
  const [transferResult, setTransferResult] = useState<{
    recipient: string
    amount: number
  } | null>(null)

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

  // Debounced user search
  useEffect(() => {
    if (mode !== "username" || !recipient || recipient.length < 2) {
      setFoundUser(null)
      return
    }

    const timer = setTimeout(async () => {
      setSearching(true)
      setError("")

      try {
        const { data } = await userApi.search(recipient)
        setFoundUser(data)
        hapticFeedback("light")
      } catch (err: any) {
        setFoundUser(null)
        if (recipient.length >= 3) {
          setError("Пользователь не найден")
        }
      } finally {
        setSearching(false)
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [recipient, mode])

  const isValidAddress = (addr: string) => /^0x[a-fA-F0-9]{40}$/.test(addr)

  const handleModeChange = (newMode: TransferMode) => {
    setMode(newMode)
    setRecipient("")
    setFoundUser(null)
    setError("")
    hapticFeedback("light")
  }

  const handleSend = async () => {
    const amountNum = parseFloat(amount)
    if (!amountNum) return

    if (amountNum > (balance?.oltin.available || 0)) {
      setError("Недостаточно OLTIN")
      hapticFeedback("error")
      return
    }

    setLoading(true)
    setError("")

    try {
      if (mode === "username") {
        // Internal transfer by username
        if (!foundUser) {
          setError("Сначала найдите пользователя")
          return
        }

        const { data } = await walletApi.transferInternal(recipient, amountNum)
        setTransferResult({
          recipient: data.recipient_username || recipient,
          amount: data.amount,
        })
        hapticFeedback("success")
        setSuccess(true)
      } else {
        // Blockchain transfer by address
        if (!isValidAddress(recipient)) {
          setError("Неверный формат адреса")
          return
        }

        const { data } = await walletApi.transfer(recipient, amountNum)
        setTxHash(data.tx_hash)
        hapticFeedback("success")
        setSuccess(true)
      }

      // Refresh balance
      const balanceRes = await walletApi.getBalance()
      setBalance(balanceRes.data)
    } catch (err: any) {
      hapticFeedback("error")
      setError(err.response?.data?.detail || "Ошибка перевода")
    } finally {
      setLoading(false)
    }
  }

  const setPreset = (percent: number) => {
    if (balance?.oltin.available) {
      const val = (balance.oltin.available * percent) / 100
      setAmount(val.toFixed(4))
      hapticFeedback("light")
    }
  }

  const canSend = () => {
    const amountNum = parseFloat(amount)
    if (!amountNum || amountNum <= 0) return false

    if (mode === "username") {
      return !!foundUser
    } else {
      return isValidAddress(recipient)
    }
  }

  // Success screen
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Card className="p-6 text-center">
          <div className="text-5xl mb-4">✓</div>
          <h2 className="text-xl font-bold text-gold mb-2">Перевод отправлен!</h2>

          {mode === "username" && transferResult ? (
            <>
              <p className="text-lg">{formatNumber(transferResult.amount, 4)} OLTIN</p>
              <p className="text-muted mt-1">→ @{transferResult.recipient}</p>
              <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3 mt-4">
                <p className="text-green-400 text-sm">✨ Мгновенный перевод без комиссии</p>
              </div>
            </>
          ) : (
            <>
              <p className="text-lg">{formatNumber(parseFloat(amount), 4)} OLTIN</p>
              {txHash && (
                <a
                  href={`https://sepolia.explorer.zksync.io/tx/${txHash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-gold underline mt-4 block"
                >
                  Посмотреть в Explorer →
                </a>
              )}
            </>
          )}

          <Button
            onClick={() => router.push("/dashboard")}
            className="mt-6 w-full"
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
        <Link href="/dashboard" className="text-muted mr-4 text-xl">←</Link>
        <h1 className="text-xl font-bold">Отправить OLTIN</h1>
      </header>

      {/* Mode switcher */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => handleModeChange("username")}
          className={`flex-1 py-3 rounded-lg font-medium transition-all ${
            mode === "username"
              ? "bg-gold text-black"
              : "bg-card border border-border text-muted"
          }`}
        >
          @username
        </button>
        <button
          onClick={() => handleModeChange("address")}
          className={`flex-1 py-3 rounded-lg font-medium transition-all ${
            mode === "address"
              ? "bg-gold text-black"
              : "bg-card border border-border text-muted"
          }`}
        >
          0x адрес
        </button>
      </div>

      <Card className="p-4 mb-4">
        <p className="text-muted text-sm mb-4">
          Доступно: <span className="text-gold font-medium">{formatNumber(balance?.oltin.available || 0, 4)} OLTIN</span>
        </p>

        {/* Recipient input */}
        <div className="mb-4">
          <label className="text-sm text-muted block mb-1">
            {mode === "username" ? "Telegram @username" : "Адрес кошелька"}
          </label>
          <Input
            type="text"
            placeholder={mode === "username" ? "@username" : "0x..."}
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            className="text-lg"
          />

          {/* Address validation */}
          {mode === "address" && recipient && !isValidAddress(recipient) && (
            <p className="text-red-500 text-xs mt-1">Неверный формат адреса</p>
          )}
        </div>

        {/* Found user display */}
        {mode === "username" && (
          <>
            {searching && (
              <div className="flex items-center gap-2 text-muted text-sm mb-4">
                <div className="w-4 h-4 border-2 border-gold border-t-transparent rounded-full animate-spin" />
                Поиск...
              </div>
            )}

            {foundUser && !searching && (
              <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3 mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center text-green-400">
                    ✓
                  </div>
                  <div>
                    <p className="text-green-400 font-medium">@{foundUser.username}</p>
                    {foundUser.first_name && (
                      <p className="text-sm text-muted">{foundUser.first_name}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Amount input */}
        <div className="mb-4">
          <label className="text-sm text-muted block mb-1">Количество OLTIN</label>
          <Input
            type="number"
            step="0.0001"
            placeholder="0.5"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="text-lg"
          />
        </div>

        {/* Preset buttons */}
        <div className="flex gap-2 mb-4">
          {[25, 50, 75, 100].map((p) => (
            <button
              key={p}
              onClick={() => setPreset(p)}
              className="flex-1 py-2 text-sm bg-background rounded-lg border border-border hover:border-gold transition-colors"
            >
              {p}%
            </button>
          ))}
        </div>

        {/* Transfer info */}
        {mode === "username" ? (
          <div className="bg-background/50 p-3 rounded-lg text-sm">
            <p className="text-green-400 mb-1">✨ Мгновенный перевод</p>
            <p className="text-muted">Без комиссии, внутри платформы OltinChain</p>
          </div>
        ) : (
          <div className="bg-background/50 p-3 rounded-lg text-sm text-muted">
            <p>⚡ Перевод через zkSync Era</p>
            <p className="mt-1">Убедитесь в правильности адреса!</p>
          </div>
        )}

        {error && (
          <p className="text-red-500 text-sm mt-3 p-2 bg-red-500/10 rounded">{error}</p>
        )}
      </Card>

      <Button
        onClick={handleSend}
        disabled={!canSend() || loading}
        className="w-full py-4 text-lg"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <div className="w-5 h-5 border-2 border-black border-t-transparent rounded-full animate-spin" />
            Отправка...
          </span>
        ) : (
          "Отправить OLTIN"
        )}
      </Button>
    </div>
  )
}
