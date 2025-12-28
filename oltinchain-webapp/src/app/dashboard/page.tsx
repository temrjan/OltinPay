"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { walletApi, priceApi } from "@/lib/api"
import { useAuthStore, useWalletStore, usePriceStore } from "@/lib/store"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

function formatNumber(n: number, decimals = 2) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

export default function DashboardPage() {
  const router = useRouter()
  const { isAuthenticated, logout } = useAuthStore()
  const { balance, setBalance } = useWalletStore()
  const { price, setPrice } = usePriceStore()
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/auth/login")
      return
    }

    const fetchData = async () => {
      try {
        const [balanceRes, priceRes] = await Promise.all([
          walletApi.getBalance(),
          priceApi.getGoldPrice(),
        ])
        setBalance(balanceRes.data)
        setPrice(priceRes.data)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [isAuthenticated, router, setBalance, setPrice])

  const copyAddress = () => {
    if (balance?.wallet_address) {
      navigator.clipboard.writeText(balance.wallet_address)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleLogout = () => {
    logout()
    router.push("/auth/login")
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-gold">Загрузка...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4 pb-20">
      <header className="flex justify-between items-center mb-6">
        <a href="https://oltinchain.com" className="text-xl font-bold text-gold hover:underline">← OltinChain</a>
        <button onClick={handleLogout} className="text-muted text-sm">
          Выйти
        </button>
      </header>

      {/* Balances */}
      <Card className="p-4 mb-4">
        <div className="flex justify-between items-start mb-4">
          <div>
            <p className="text-muted text-sm">Баланс UZS</p>
            <p className="text-2xl font-bold">{formatNumber(balance?.uzs.available || 0, 0)} UZS</p>
          </div>
          <div className="text-right">
            <p className="text-muted text-sm">Баланс OLTIN</p>
            <p className="text-2xl font-bold text-gold">{formatNumber(balance?.oltin.available || 0, 4)} г</p>
          </div>
        </div>
        
        {balance?.wallet_address && (
          <div className="border-t border-border pt-3">
            <p className="text-muted text-xs mb-1">Адрес кошелька</p>
            <button
              onClick={copyAddress}
              className="text-xs font-mono bg-background p-2 rounded w-full text-left truncate"
            >
              {copied ? "✓ Скопировано" : balance.wallet_address}
            </button>
          </div>
        )}
      </Card>

      {/* Price */}
      {price && (
        <Card className="p-4 mb-4">
          <p className="text-muted text-sm mb-2">Цена золота (1 грамм)</p>
          <div className="flex justify-between">
            <div>
              <p className="text-xs text-muted">Покупка</p>
              <p className="text-lg font-bold text-green-500">{formatNumber(price.buy_price, 0)} UZS</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted">Продажа</p>
              <p className="text-lg font-bold text-red-400">{formatNumber(price.sell_price, 0)} UZS</p>
            </div>
          </div>
        </Card>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <Link href="/buy">
          <Button className="w-full bg-green-600 hover:bg-green-700">Купить</Button>
        </Link>
        <Link href="/sell">
          <Button className="w-full bg-red-500 hover:bg-red-600">Продать</Button>
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Link href="/send">
          <Button variant="outline" className="w-full">Отправить</Button>
        </Link>
        <Link href="/history">
          <Button variant="outline" className="w-full">История</Button>
        </Link>
      </div>
    </div>
  )
}
