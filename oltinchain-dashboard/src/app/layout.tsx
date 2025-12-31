import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "OltinChain Dashboard",
  description: "Real-time dashboard for OltinChain - Tokenized Gold Platform",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen`}>
        {/* Header */}
        <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-sm sticky top-0 z-50">
          <div className="w-full px-4 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🪙</span>
              <a href="https://oltinchain.com" className="text-xl font-bold text-gold-gradient hover:opacity-80">OltinChain</a>
              <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-1 rounded hidden sm:inline">zkSync Sepolia</span>
            </div>
            
            <nav className="hidden lg:flex items-center gap-6">
              <a href="/" className="text-sm text-zinc-400 hover:text-amber-400 transition-colors">Dashboard</a>
              <a href="/oltindex" className="text-sm text-zinc-400 hover:text-amber-400 transition-colors flex items-center gap-1">📈 Биржа</a>
              <a href="/bots" className="text-sm text-zinc-400 hover:text-amber-400 transition-colors flex items-center gap-1">🤖 Auction Bots</a>
              <div className="h-4 w-px bg-zinc-700" />
              <a href="https://sepolia.explorer.zksync.io/address/0xA7E92168517864359B6Fa9e2247B01e0280A7dAa" target="_blank" rel="noopener noreferrer" className="text-sm text-zinc-400 hover:text-amber-400 transition-colors">Contract ↗</a>
              <a href="https://api.oltinchain.com/docs" target="_blank" rel="noopener noreferrer" className="text-sm text-zinc-400 hover:text-amber-400 transition-colors">API Docs ↗</a>
            </nav>

            {/* Mobile menu */}
            <div className="lg:hidden">
              <details className="relative">
                <summary className="list-none cursor-pointer p-2 text-zinc-400 hover:text-white">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </summary>
                <div className="absolute right-0 top-full mt-2 w-48 bg-zinc-800 border border-zinc-700 rounded-lg shadow-lg py-2 z-50">
                  <a href="/" className="block px-4 py-2 text-sm text-zinc-400 hover:text-amber-400 hover:bg-zinc-700">Dashboard</a>
                  <a href="/oltindex" className="block px-4 py-2 text-sm text-zinc-400 hover:text-amber-400 hover:bg-zinc-700">📈 Биржа</a>
                  <a href="/bots" className="block px-4 py-2 text-sm text-zinc-400 hover:text-amber-400 hover:bg-zinc-700">🤖 Auction Bots</a>
                  <div className="border-t border-zinc-700 my-2" />
                  <a href="https://sepolia.explorer.zksync.io/address/0xA7E92168517864359B6Fa9e2247B01e0280A7dAa" target="_blank" className="block px-4 py-2 text-sm text-zinc-400 hover:text-amber-400 hover:bg-zinc-700">Contract ↗</a>
                  <a href="https://api.oltinchain.com/docs" target="_blank" className="block px-4 py-2 text-sm text-zinc-400 hover:text-amber-400 hover:bg-zinc-700">API Docs ↗</a>
                </div>
              </details>
            </div>
          </div>
        </header>

        {/* Main content - full width */}
        <main className="w-full px-4 lg:px-8 py-6">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-zinc-800 py-6 mt-auto">
          <div className="w-full px-4 lg:px-8 text-center text-sm text-zinc-500">
            <p>OltinChain © 2025 — 1 OLTIN = 1 gram of physical gold</p>
            <p className="mt-1">Demo platform on zkSync Sepolia testnet</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
