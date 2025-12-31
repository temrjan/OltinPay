"use client";

import { useState, useEffect, useCallback } from "react";
import { LiveMatchWidget } from "@/components/LiveMatchWidget";

// Types
interface Trade {
  id: string;
  side: "BUY" | "SELL";
  price: string;
  amount: string;
  total: string;
  bot_id: string;
  bot_type: string;
  timestamp: string;
}

interface OrderBookEntry {
  price: string;
  amount: string;
  total: string;
  bot_count: number;
}

interface OrderBookData {
  asks: OrderBookEntry[];
  bids: OrderBookEntry[];
  spread: string;
  spread_percent: string;
}

interface CycleInfo {
  cycle_id: number;
  phase: string;
  orders_count: number;
  buy_volume: string;
  sell_volume: string;
  imbalance: string;
  deviation: string;
}

interface MatchInfo {
  match_id: string;
  started_at: string;
  cycles_completed: number;
  current_leader: string;
  deviation: string;
  target_price: string;
  market_price: string;
}

interface Stats {
  total_bots: number;
  traders: number;
  whales: number;
  market_makers: number;
  active_bots: number;
  total_volume_usd: string;
  total_trades: number;
}

interface DashboardData {
  match: MatchInfo;
  current_cycle: CycleInfo | null;
  stats: Stats;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.oltinchain.com";

export default function BotsDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [orderbook, setOrderbook] = useState<OrderBookData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, tradesRes, orderbookRes] = await Promise.all([
        fetch(`${API_URL}/bots/status`),
        fetch(`${API_URL}/bots/trades?limit=30`),
        fetch(`${API_URL}/bots/orderbook`),
      ]);

      if (statusRes.ok) setData(await statusRes.json());
      if (tradesRes.ok) setTrades(await tradesRes.json());
      if (orderbookRes.ok) setOrderbook(await orderbookRes.json());
      setLastUpdate(new Date());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-xl animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-gray-900/95 backdrop-blur border-b border-gray-800 px-3 py-3 sm:px-6 sm:py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg sm:text-2xl font-bold text-yellow-500">🏦 Auction Waves</h1>
            <p className="text-xs sm:text-sm text-gray-400 hidden sm:block">OltinChain Trading Dashboard</p>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <span className="text-[10px] sm:text-xs text-gray-500">
              Updated: {lastUpdate.toLocaleTimeString()}
            </span>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-green-400 text-xs sm:text-sm font-medium">LIVE</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-3 sm:p-4 lg:p-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6">
          
          {/* Live Match Widget */}
          <div className="lg:col-span-4 xl:col-span-3">
            <LiveMatchWidget match={data?.match || null} />
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-8 xl:col-span-9 space-y-4 lg:space-y-6">
            
            {/* Quick Stats */}
            <div className="flex gap-2 sm:gap-3 overflow-x-auto pb-2 sm:pb-0 -mx-3 px-3 sm:mx-0 sm:px-0 sm:grid sm:grid-cols-4">
              <QuickStat label="Market" value={`$${formatPrice(data?.match?.market_price || "0")}`} />
              <QuickStat label="Target" value={`$${formatPrice(data?.match?.target_price || "0")}`} className="text-yellow-400" />
              <QuickStat label="Trades" value={String(data?.stats?.total_trades || 0)} />
              <QuickStat label="Volume" value={`$${formatPrice(data?.stats?.total_volume_usd || "0")}`} />
            </div>

            {/* Cycle + Trades */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <AuctionCycle cycle={data?.current_cycle} />
              <TradeFeed trades={trades} />
            </div>

            {/* Order Book - Now with real data */}
            <OrderBook data={orderbook} />

            {/* Bot Stats */}
            <BotStats stats={data?.stats} />
          </div>
        </div>
      </main>
    </div>
  );
}

function QuickStat({ label, value, className = "" }: { label: string; value: string; className?: string }) {
  return (
    <div className="flex-shrink-0 bg-gray-800 rounded-lg px-3 py-2 sm:px-4 sm:py-3 min-w-[80px] sm:min-w-0">
      <div className="text-[10px] sm:text-xs text-gray-400 uppercase">{label}</div>
      <div className={`text-sm sm:text-lg font-bold ${className}`}>{value}</div>
    </div>
  );
}

// Order Book - Now fetches real data from API
function OrderBook({ data }: { data: OrderBookData | null }) {
  const asks = data?.asks?.slice(0, 6) || [];
  const bids = data?.bids?.slice(0, 6) || [];
  const spread = data?.spread ? parseFloat(data.spread) : 0;
  const spreadPct = data?.spread_percent ? parseFloat(data.spread_percent) : 0;

  // Calculate max volume for bar visualization
  const maxAskVol = Math.max(...asks.map(a => parseFloat(a.amount) || 0), 1);
  const maxBidVol = Math.max(...bids.map(b => parseFloat(b.amount) || 0), 1);

  return (
    <div className="bg-gray-800 rounded-xl p-3 sm:p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base sm:text-lg font-bold text-yellow-500">📊 Order Book</h2>
        <span className="text-xs text-gray-400">
          Spread: <span className={`font-bold ${spread < 0 ? 'text-red-400' : 'text-green-400'}`}>
            {spreadPct.toFixed(2)}%
          </span>
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        {/* Asks (Sell) */}
        <div>
          <div className="text-xs text-red-400 mb-2 font-medium flex justify-between">
            <span>SELL</span>
            <span className="text-gray-500">Amount</span>
          </div>
          {asks.length > 0 ? asks.map((o, i) => {
            const vol = parseFloat(o.amount) || 0;
            const pct = (vol / maxAskVol) * 100;
            return (
              <div key={i} className="relative flex justify-between text-xs sm:text-sm py-1">
                <div 
                  className="absolute right-0 top-0 h-full bg-red-500/20" 
                  style={{ width: `${pct}%` }}
                />
                <span className="text-red-400 relative z-10">${parseFloat(o.price).toFixed(2)}</span>
                <span className="text-gray-300 relative z-10">{vol.toFixed(2)}g</span>
              </div>
            );
          }) : (
            <div className="text-gray-500 text-xs py-2">No sell orders</div>
          )}
        </div>
        
        {/* Bids (Buy) */}
        <div>
          <div className="text-xs text-green-400 mb-2 font-medium flex justify-between">
            <span>BUY</span>
            <span className="text-gray-500">Amount</span>
          </div>
          {bids.length > 0 ? bids.map((o, i) => {
            const vol = parseFloat(o.amount) || 0;
            const pct = (vol / maxBidVol) * 100;
            return (
              <div key={i} className="relative flex justify-between text-xs sm:text-sm py-1">
                <div 
                  className="absolute left-0 top-0 h-full bg-green-500/20" 
                  style={{ width: `${pct}%` }}
                />
                <span className="text-green-400 relative z-10">${parseFloat(o.price).toFixed(2)}</span>
                <span className="text-gray-300 relative z-10">{vol.toFixed(2)}g</span>
              </div>
            );
          }) : (
            <div className="text-gray-500 text-xs py-2">No buy orders</div>
          )}
        </div>
      </div>
      
      {/* Orders count */}
      <div className="mt-3 pt-3 border-t border-gray-700 flex justify-between text-xs text-gray-400">
        <span>Sell orders: {asks.reduce((s, a) => s + (a.bot_count || 0), 0)}</span>
        <span>Buy orders: {bids.reduce((s, b) => s + (b.bot_count || 0), 0)}</span>
      </div>
    </div>
  );
}

function AuctionCycle({ cycle }: { cycle: CycleInfo | null | undefined }) {
  const phase = cycle?.phase || "ACCUMULATE";
  const imbalance = parseFloat(cycle?.imbalance || "0");
  const buyPct = Math.max(10, Math.min(90, 50 + imbalance / 2));
  
  return (
    <div className="bg-gray-800 rounded-xl p-3 sm:p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base sm:text-lg font-bold text-yellow-500">⚡ Cycle</h2>
        <span className={`px-2 py-0.5 sm:px-3 sm:py-1 rounded-full text-xs font-bold ${
          phase === "ACCUMULATE" ? "bg-blue-600" : "bg-purple-600"
        }`}>
          {phase}
        </span>
      </div>

      <div className="space-y-2 text-xs sm:text-sm">
        <div className="flex justify-between">
          <span className="text-gray-400">Cycle #</span>
          <span className="font-bold">{cycle?.cycle_id || 0}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Orders</span>
          <span className="font-bold">{cycle?.orders_count || 0}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Buy Vol</span>
          <span className="text-green-400 font-bold">${formatPrice(cycle?.buy_volume || "0")}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Sell Vol</span>
          <span className="text-red-400 font-bold">${formatPrice(cycle?.sell_volume || "0")}</span>
        </div>
      </div>

      <div className="mt-3">
        <div className="flex h-3 sm:h-4 rounded-full overflow-hidden">
          <div className="bg-green-500 flex items-center justify-center" style={{ width: `${buyPct}%` }}>
            <span className="text-[8px] sm:text-[10px] font-bold">{buyPct > 25 ? `${buyPct.toFixed(0)}%` : ''}</span>
          </div>
          <div className="bg-red-500 flex items-center justify-center" style={{ width: `${100-buyPct}%` }}>
            <span className="text-[8px] sm:text-[10px] font-bold">{(100-buyPct) > 25 ? `${(100-buyPct).toFixed(0)}%` : ''}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function TradeFeed({ trades }: { trades: Trade[] }) {
  return (
    <div className="bg-gray-800 rounded-xl p-3 sm:p-4">
      <h2 className="text-base sm:text-lg font-bold mb-3 text-yellow-500">📜 Trades</h2>
      
      {trades.length > 0 ? (
        <div className="space-y-1 max-h-48 sm:max-h-56 overflow-y-auto">
          {trades.slice(0, 10).map((t) => (
            <div key={t.id} className="flex items-center justify-between py-1.5 border-b border-gray-700/50 text-xs sm:text-sm">
              <span className={t.side === "BUY" ? "text-green-400" : "text-red-400"}>
                {t.side === "BUY" ? "▲" : "▼"} {t.side}
              </span>
              <span className="text-gray-300">${parseFloat(t.price).toFixed(2)}</span>
              <span className="text-gray-400">{parseFloat(t.amount).toFixed(2)}g</span>
              <span className="text-gray-500 text-[10px] sm:text-xs w-6 text-center bg-gray-700 rounded">{t.bot_type}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-gray-500 text-sm text-center py-8">
          No recent trades
        </div>
      )}
    </div>
  );
}

function BotStats({ stats }: { stats?: Stats }) {
  return (
    <div className="bg-gray-800 rounded-xl p-3 sm:p-4">
      <h2 className="text-base sm:text-lg font-bold mb-3 text-yellow-500">🤖 Bots</h2>
      
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 sm:gap-4">
        <StatBadge value={stats?.total_bots || 50} label="Total" color="text-blue-400" />
        <StatBadge value={stats?.traders || 42} label="Traders" color="text-green-400" />
        <StatBadge value={stats?.whales || 2} label="Whales" color="text-purple-400" />
        <StatBadge value={stats?.market_makers || 6} label="MM" color="text-yellow-400" />
        <StatBadge value={stats?.active_bots || 50} label="Active" color="text-cyan-400" />
        <div className="text-center">
          <div className="text-sm sm:text-lg font-bold text-white">${formatPrice(stats?.total_volume_usd || "0")}</div>
          <div className="text-[10px] sm:text-xs text-gray-400">Volume</div>
        </div>
      </div>
    </div>
  );
}

function StatBadge({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="text-center">
      <div className={`text-lg sm:text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-[10px] sm:text-xs text-gray-400">{label}</div>
    </div>
  );
}

function formatPrice(price: string | number): string {
  const num = typeof price === "string" ? parseFloat(price) : price;
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return Math.round(num).toString();
}
