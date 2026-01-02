import TradingWidget from '@/components/TradingWidget';
import OltinPriceChart from '@/components/OltinPriceChart';
import OrderBookWidget from '@/components/OrderBookWidget';
import RecentTrades from '@/components/RecentTrades';

export default function TradePage() {
  return (
    <div className="space-y-6">
      {/* Top row: Chart + Trading widget */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Chart - takes 3 columns on large screens */}
        <div className="lg:col-span-3">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4 text-white">OLTIN/USD</h2>
            <div className="h-[400px]">
              <OltinPriceChart />
            </div>
          </div>
        </div>

        {/* Trading widget */}
        <div className="lg:col-span-1">
          <TradingWidget />
        </div>
      </div>

      {/* Middle row: OrderBook + Recent Trades */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OrderBookWidget depth={20} />
        <RecentTrades />
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-green-600/20 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div>
              <p className="text-zinc-500 text-sm">Фаза рынка</p>
              <p className="text-white font-medium">Markup (Рост)</p>
            </div>
          </div>
          <p className="text-zinc-600 text-sm">
            Цена активно растет. Оптимальное время для холда.
          </p>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="text-zinc-500 text-sm">Модель цены</p>
              <p className="text-white font-medium">Wyckoff + Bitcoin</p>
            </div>
          </div>
          <p className="text-zinc-600 text-sm">
            1 неделя = 1 год Bitcoin. Циклы роста и коррекции.
          </p>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-600/20 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <p className="text-zinc-500 text-sm">Безопасность</p>
              <p className="text-white font-medium">zkSync Era</p>
            </div>
          </div>
          <p className="text-zinc-600 text-sm">
            Токены обеспечены реальным золотом на блокчейне.
          </p>
        </div>
      </div>
    </div>
  );
}
