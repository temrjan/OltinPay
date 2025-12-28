'use client';

import { LiveMetrics } from '@/components/LiveMetrics';
import { PriceChart } from '@/components/PriceChart';
import { ProofOfReserves } from '@/components/ProofOfReserves';
import { GoldBarLookup } from '@/components/GoldBarLookup';
import { TransactionFeed } from '@/components/TransactionFeed';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Hero section */}
      <section className="text-center py-8">
        <h2 className="text-4xl font-bold text-gold-gradient mb-2">
          Tokenized Gold Platform
        </h2>
        <p className="text-zinc-400 max-w-2xl mx-auto">
          Real-time dashboard for OltinChain — track gold prices, token supply, 
          transactions, and verify proof of reserves on zkSync.
        </p>
      </section>

      {/* Live Metrics */}
      <section>
        <LiveMetrics />
      </section>

      {/* Main Grid */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Price Chart - takes 2 columns */}
        <div className="lg:col-span-2">
          <PriceChart />
        </div>
        
        {/* Transaction Feed */}
        <div className="lg:col-span-1">
          <TransactionFeed />
        </div>
      </section>

      {/* Proof of Reserves & Lookup */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ProofOfReserves />
        <GoldBarLookup />
      </section>
    </div>
  );
}
