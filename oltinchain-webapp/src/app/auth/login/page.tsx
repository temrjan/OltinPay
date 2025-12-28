"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { authApi } from "@/lib/api"
import { useAuthStore } from "@/lib/store"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"

export default function LoginPage() {
  const router = useRouter()
  const { setAuth } = useAuthStore()
  const [phone, setPhone] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      const { data } = await authApi.login(phone, password)
      localStorage.setItem("access_token", data.access_token)
      localStorage.setItem("refresh_token", data.refresh_token)
      setAuth(data.user, data.access_token, data.refresh_token)
      router.push("/dashboard")
    } catch (err: any) {
      setError(err.response?.data?.detail || "Ошибка входа")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-6">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-gold">OltinChain</h1>
          <p className="text-muted mt-2">Вход в кошелёк</p>
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
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Вход..." : "Войти"}
          </Button>
        </form>

        <p className="text-center mt-4 text-sm text-muted">
          Нет аккаунта?{" "}
          <Link href="/auth/register" className="text-gold hover:underline">
            Регистрация
          </Link>
        </p>
      </Card>
    </div>
  )
}
