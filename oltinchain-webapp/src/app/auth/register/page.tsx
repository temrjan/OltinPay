"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { authApi } from "@/lib/api"
import { useAuthStore } from "@/lib/store"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"

export default function RegisterPage() {
  const router = useRouter()
  const { setAuth } = useAuthStore()
  const [phone, setPhone] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (password !== confirm) {
      setError("Пароли не совпадают")
      return
    }

    if (password.length < 6) {
      setError("Пароль минимум 6 символов")
      return
    }

    setLoading(true)

    try {
      const { data } = await authApi.register(phone, password)
      localStorage.setItem("access_token", data.access_token)
      localStorage.setItem("refresh_token", data.refresh_token)
      setAuth(data.user, data.access_token, data.refresh_token)
      router.push("/dashboard")
    } catch (err: any) {
      setError(err.response?.data?.detail || "Ошибка регистрации")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-6">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-gold">OltinChain</h1>
          <p className="text-muted mt-2">Создать кошелёк</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm text-muted">Телефон</label>
            <Input
              type="tel"
              placeholder="+998901234567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="text-sm text-muted">Пароль</label>
            <Input
              type="password"
              placeholder="Минимум 6 символов"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="text-sm text-muted">Подтвердите пароль</label>
            <Input
              type="password"
              placeholder="••••••••"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Регистрация..." : "Создать кошелёк"}
          </Button>
        </form>

        <p className="text-center mt-4 text-sm text-muted">
          Уже есть аккаунт?{" "}
          <Link href="/auth/login" className="text-gold hover:underline">
            Войти
          </Link>
        </p>

        <p className="text-center mt-4 text-xs text-muted">
          🎁 Бонус при регистрации: 1,000,000 UZS
        </p>
      </Card>
    </div>
  )
}
