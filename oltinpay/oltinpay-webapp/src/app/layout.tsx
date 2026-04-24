import type { Metadata, Viewport } from 'next';
import Script from 'next/script';
import { Providers } from './providers';
import { BottomNav } from '@/components/layout/BottomNav';
import './globals.css';

export const metadata: Metadata = {
  title: 'OltinPay',
  description: 'Telegram Mini App for tokenized gold trading',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="uz">
      <body className="bg-background text-text-primary min-h-screen">
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
        <Providers>
          <main className="pb-16">
            {children}
          </main>
          <BottomNav />
        </Providers>
      </body>
    </html>
  );
}
