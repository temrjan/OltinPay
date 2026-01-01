import type { Metadata, Viewport } from "next"
import { Providers } from "@/components/Providers"
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
      <body className="min-h-screen bg-background text-white antialiased">
        <Providers>
          <main className="max-w-lg mx-auto">{children}</main>
        </Providers>
      </body>
    </html>
  )
}
