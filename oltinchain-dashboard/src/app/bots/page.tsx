"use client";

import { useState, useEffect, useCallback } from "react";
import { Card } from "@/components/Card";

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

interface CycleInfo {
  cycle_id: number;
  phase: string;
  started_at: string;
  duration_seconds: number | null;
  orders_count: number;
  buy_volume: string;
  sell_volume: string;
  imbalance: string;
  price_before: string;
  price_after: string | null;
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
  price_history: { price: string; timestamp: string }[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.oltinchain.com";

export default function BotsDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, tradesRes] = await Promise.all([
        fetch(`${API_URL}/bots/status`),
        fetch(`${API_URL}/bots/trades?limit=30`),
      ]);

      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setData(statusData);
      }

      if (tradesRes.ok) {
        const tradesData = await tradesRes.json();
        setTrades(tradesData);
      }

      setError(null);
    } catch (err) {
      setError("Failed to fetch data");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000); // Update every 3 seconds
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-6 flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  const deviation = data?.match?.deviation ? parseFloat(data.match.deviation) * 100 : 0;
  const deviationColor = deviation < 0 ? "text-red-400" : deviation > 0 ? "text-green-400" : "text-gray-400";

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-yellow-500">🏦 Auction Waves Trading</h1>
        <p className="text-gray-400">OltinChain Bot Dashboard</p>
      </div>

      {/* Top Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
        <StatCard 
          label="Market Price" 
          value={formatPrice(data?.match?.market_price || "0")} 
          suffix="USD"
        />
        <StatCard 
          label="Target Price" 
          value={formatPrice(data?.match?.target_price || "0")} 
          suffix="USD"
          className="text-yellow-400"
        />
        <StatCard 
          label="Deviation" 
          value={`${deviation.toFixed(2)}%`}
          className={deviationColor}
        />
        <StatCard 
          label="Leader" 
          value={data?.match?.current_leader || "—"}
          className={data?.match?.current_leader === "BUYERS" ? "text-green-400" : "text-red-400"}
        />
        <StatCard 
          label="Cycles" 
          value={String(data?.match?.cycles_completed || 0)}
        />
        <StatCard 
          label="Total Trades" 
          value={String(data?.stats?.total_trades || 0)}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Order Book */}
        <div className="lg:col-span-1">
          <OrderBook />
        </div>

        {/* Center Column - Auction Cycle */}
        <div className="lg:col-span-1">
          <AuctionCycle cycle={data?.current_cycle} />
        </div>

        {/* Right Column - Trade Feed */}
        <div className="lg:col-span-1">
          <TradeFeed trades={trades} />
        </div>
      </div>

      {/* Bottom - Bot Stats */}
      <div className="mt-6">
        <BotStats stats={data?.stats} />
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({ label, value, suffix, className = "" }: { 
  label: string; 
  value: string; 
  suffix?: string;
  className?: string;
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="text-gray-400 text-xs uppercase">{label}</div>
      <div className={`text-lg font-bold ${className}`}>
        {value} {suffix && <span className="text-sm font-normal">{suffix}</span>}
      </div>
    </div>
  );
}

// Order Book Component
function OrderBook() {
  const [asks, setAsks] = useState<OrderBookEntry[]>([]);
  const [bids, setBids] = useState<OrderBookEntry[]>([]);

  // Generate sample data for visualization
  useEffect(() => {
    const generateOrders = (basePrice: number, isBuy: boolean): OrderBookEntry[] => {
      const orders: OrderBookEntry[] = [];
      for (let i = 0; i < 8; i++) {
        const priceDiff = (i + 1) * (isBuy ? -0.05 : 0.05);
        const price = basePrice + priceDiff;
        const amount = (Math.random() * 10 + 1).toFixed(4);
        orders.push({
          price: price.toString(),
          amount,
          total: (price * parseFloat(amount)).toFixed(0),
          bot_count: Math.floor(Math.random() * 5) + 1,
        });
      }
      return orders;
    };

    const basePrice = 61;
    setAsks(generateOrders(basePrice, false));
    setBids(generateOrders(basePrice, true));
  }, []);

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full">
      <h2 className="text-lg font-bold mb-4 text-yellow-500">📊 Order Book</h2>
      
      {/* Headers */}
      <div className="grid grid-cols-3 text-xs text-gray-400 mb-2">
        <div>Price (USD)</div>
        <div className="text-right">Amount (g)</div>
        <div className="text-right">Total</div>
      </div>

      {/* Asks (Sell orders) */}
      <div className="mb-4">
        {asks.slice().reverse().map((order, i) => (
          <div key={`ask-${i}`} className="grid grid-cols-3 text-sm py-1 hover:bg-gray-700">
            <div className="text-red-400">{formatPrice(order.price)}</div>
            <div className="text-right">{order.amount}</div>
            <div className="text-right text-gray-400">{formatPrice(order.total)}</div>
          </div>
        ))}
      </div>

      {/* Spread */}
      <div className="text-center py-2 bg-gray-700 rounded text-sm mb-4">
        <span className="text-yellow-400 font-bold">61.00</span>
        <span className="text-gray-400 ml-2">Spread: 0.15%</span>
      </div>

      {/* Bids (Buy orders) */}
      <div>
        {bids.map((order, i) => (
          <div key={`bid-${i}`} className="grid grid-cols-3 text-sm py-1 hover:bg-gray-700">
            <div className="text-green-400">{formatPrice(order.price)}</div>
            <div className="text-right">{order.amount}</div>
            <div className="text-right text-gray-400">{formatPrice(order.total)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Auction Cycle Component
function AuctionCycle({ cycle }: { cycle: CycleInfo | null | undefined }) {
  const phase = cycle?.phase || "ACCUMULATE";
  const isAccumulate = phase === "ACCUMULATE";
  
  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full">
      <h2 className="text-lg font-bold mb-4 text-yellow-500">⚡ Current Auction Cycle</h2>
      
      {/* Cycle Info */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <span className="text-gray-400">Cycle #{cycle?.cycle_id || 1}</span>
          <span className={`px-3 py-1 rounded-full text-sm font-bold ${
            isAccumulate ? "bg-blue-600" : "bg-purple-600"
          }`}>
            {phase}
          </span>
        </div>

        {/* Phase Progress */}
        <div className="relative h-8 bg-gray-700 rounded-full overflow-hidden mb-4">
          <div 
            className={`absolute h-full transition-all duration-1000 ${
              isAccumulate ? "bg-blue-500" : "bg-purple-500"
            }`}
            style={{ width: isAccumulate ? "60%" : "100%" }}
          />
          <div className="absolute inset-0 flex items-center justify-center text-sm font-bold">
            {isAccumulate ? "Collecting Orders..." : "Executing..."}
          </div>
        </div>
      </div>

      {/* Cycle Stats */}
      <div className="space-y-3">
        <div className="flex justify-between">
          <span className="text-gray-400">Orders</span>
          <span className="font-bold">{cycle?.orders_count || 0}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Buy Volume</span>
          <span className="text-green-400 font-bold">
            {formatPrice(cycle?.buy_volume || "0")} USD
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Sell Volume</span>
          <span className="text-red-400 font-bold">
            {formatPrice(cycle?.sell_volume || "0")} USD
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Imbalance</span>
          <span className={`font-bold ${
            parseFloat(cycle?.imbalance || "0") > 0 ? "text-green-400" : "text-red-400"
          }`}>
            {parseFloat(cycle?.imbalance || "0").toFixed(1)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Deviation</span>
          <span className="text-yellow-400 font-bold">
            {((parseFloat(cycle?.deviation || "0")) * 100).toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Visual Imbalance Bar */}
      <div className="mt-6">
        <div className="text-xs text-gray-400 mb-2">Buy/Sell Imbalance</div>
        <div className="flex h-6 rounded-full overflow-hidden">
          <div className="bg-green-500 flex items-center justify-center text-xs" style={{ width: "80%" }}>
            BUY 80%
          </div>
          <div className="bg-red-500 flex items-center justify-center text-xs" style={{ width: "20%" }}>
            20%
          </div>
        </div>
      </div>
    </div>
  );
}

// Trade Feed Component
function TradeFeed({ trades }: { trades: Trade[] }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full">
      <h2 className="text-lg font-bold mb-4 text-yellow-500">📜 Trade Feed</h2>
      
      {/* Headers */}
      <div className="grid grid-cols-4 text-xs text-gray-400 mb-2">
        <div>Side</div>
        <div className="text-right">Price</div>
        <div className="text-right">Amount</div>
        <div className="text-right">Bot</div>
      </div>

      {/* Trades List */}
      <div className="space-y-1 max-h-96 overflow-y-auto">
        {trades.length > 0 ? (
          trades.map((trade) => (
            <div 
              key={trade.id} 
              className="grid grid-cols-4 text-sm py-2 hover:bg-gray-700 border-b border-gray-700"
            >
              <div className={trade.side === "BUY" ? "text-green-400" : "text-red-400"}>
                {trade.side === "BUY" ? "▲ BUY" : "▼ SELL"}
              </div>
              <div className="text-right">{formatPrice(trade.price)}</div>
              <div className="text-right">{parseFloat(trade.amount).toFixed(2)}g</div>
              <div className="text-right text-gray-400 text-xs">
                {trade.bot_type.charAt(0).toUpperCase()}
              </div>
            </div>
          ))
        ) : (
          // Sample trades for demo
          Array.from({ length: 10 }).map((_, i) => (
            <div 
              key={i} 
              className="grid grid-cols-4 text-sm py-2 hover:bg-gray-700 border-b border-gray-700"
            >
              <div className={i % 3 === 0 ? "text-red-400" : "text-green-400"}>
                {i % 3 === 0 ? "▼ SELL" : "▲ BUY"}
              </div>
              <div className="text-right">{(60 + Math.random() * 2).toFixed(2)}</div>
              <div className="text-right">{(Math.random() * 5 + 0.5).toFixed(2)}g</div>
              <div className="text-right text-gray-400 text-xs">
                {["T", "W", "M"][Math.floor(Math.random() * 3)]}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// Bot Stats Component
function BotStats({ stats }: { stats?: Stats }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h2 className="text-lg font-bold mb-4 text-yellow-500">🤖 Bot Statistics</h2>
      
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <div className="text-center">
          <div className="text-3xl font-bold text-blue-400">{stats?.total_bots || 50}</div>
          <div className="text-gray-400 text-sm">Total Bots</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold text-green-400">{stats?.traders || 42}</div>
          <div className="text-gray-400 text-sm">Traders</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold text-purple-400">{stats?.whales || 2}</div>
          <div className="text-gray-400 text-sm">Whales</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold text-yellow-400">{stats?.market_makers || 6}</div>
          <div className="text-gray-400 text-sm">Market Makers</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold text-cyan-400">{stats?.active_bots || 50}</div>
          <div className="text-gray-400 text-sm">Active</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-white">
            {formatPrice(stats?.total_volume_usd || "0")}
          </div>
          <div className="text-gray-400 text-sm">Volume (USD)</div>
        </div>
      </div>
    </div>
  );
}

// Helper function
function formatPrice(price: string | number): string {
  const num = typeof price === "string" ? parseFloat(price) : price;
  return new Intl.NumberFormat("en-US").format(Math.round(num));
}
