import type { Metadata, Viewport } from "next"
import Script from "next/script"
import { Providers } from "@/components/Providers"
import { TelegramAuthProvider } from "@/components/TelegramAuthProvider"
import "./globals.css"

export const metadata: Metadata = {
  title: "OltinChain - Invest in Gold",
  description: "Buy, sell, and transfer tokenized gold",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "OltinChain",
  },
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#07070a",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru" className="dark">
      <head>
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
      </head>
      <body className="min-h-screen bg-background text-white antialiased">
        <Providers>
          <TelegramAuthProvider>
            <main className="max-w-lg mx-auto">{children}</main>
          </TelegramAuthProvider>
        </Providers>
      </body>
    </html>
  )
}
