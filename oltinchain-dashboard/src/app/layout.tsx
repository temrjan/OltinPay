import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'OltinChain Dashboard',
  description: 'Real-time dashboard for OltinChain - Tokenized Gold Platform',
  icons: {
    icon: '/favicon.ico',
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
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🪙</span>
              <h1 className="text-xl font-bold text-gold-gradient">OltinChain</h1>
              <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-1 rounded">zkSync Sepolia</span>
            </div>
            
            <nav className="flex items-center gap-4">
              <a 
                href="https://sepolia.explorer.zksync.io/address/0xA7E92168517864359B6Fa9e2247B01e0280A7dAa" 
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-zinc-400 hover:text-amber-400 transition-colors"
              >
                Contract ↗
              </a>
              <a 
                href="https://api.oltinchain.com/docs" 
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-zinc-400 hover:text-amber-400 transition-colors"
              >
                API Docs ↗
              </a>
            </nav>
          </div>
        </header>

        {/* Main content */}
        <main className="container mx-auto px-4 py-6">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-zinc-800 py-6 mt-auto">
          <div className="container mx-auto px-4 text-center text-sm text-zinc-500">
            <p>OltinChain © 2025 — 1 OLTIN = 1 gram of physical gold</p>
            <p className="mt-1">Demo platform on zkSync Sepolia testnet</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
