"use client"
import { Component, ReactNode } from "react"

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="min-h-screen flex items-center justify-center p-4">
            <div className="text-center">
              <h2 className="text-xl font-bold text-red-500 mb-2">
                Что-то пошло не так
              </h2>
              <p className="text-muted mb-4">
                Произошла ошибка. Попробуйте обновить страницу.
              </p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-gold text-black rounded-lg"
              >
                Обновить
              </button>
            </div>
          </div>
        )
      )
    }
    return this.props.children
  }
}
