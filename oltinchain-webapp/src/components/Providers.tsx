"use client"
import { ReactNode } from "react"
import { ErrorBoundary } from "./ErrorBoundary"

interface Props {
  children: ReactNode
}

export function Providers({ children }: Props) {
  return <ErrorBoundary>{children}</ErrorBoundary>
}
