import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'OltinChain - Invest in Gold',
  description: 'Buy, sell, and transfer tokenized gold',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-background">
        {children}
      </body>
    </html>
  )
}
