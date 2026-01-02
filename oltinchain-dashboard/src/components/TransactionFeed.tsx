'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './Card';
import { useWebSocket } from '@/hooks/useWebSocket';
import { formatNumber, formatTimeAgo } from '@/lib/utils';

interface Trade {
  id: string;
  price: string;
  quantity: string;
  taker_side: 'buy' | 'sell';
  created_at: string;
}

export function TransactionFeed() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  const { isConnected, lastMessage } = useWebSocket({
    channels: ['trades'],
  });

  // Fetch initial trades from API
  useEffect(() => {
    async function fetchInitialTrades() {
      try {
        const response = await fetch('https://api.oltinchain.com/orderbook/trades?limit=20');
        if (response.ok) {
          const data = await response.json();
          setTrades(data.trades || []);
        }
      } catch (error) {
        console.error('Failed to fetch trades:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchInitialTrades();
  }, []);

  // Handle new trades from WebSocket
  useEffect(() => {
    if (lastMessage?.type === 'trade') {
      const msg = lastMessage as { type: string; data: Trade };
      const newTrade = msg.data;
      setTrades((prev) => [newTrade, ...prev].slice(0, 50));
    }
  }, [lastMessage]);

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Live Trades</CardTitle>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-xs text-zinc-500">
            {isConnected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </CardHeader>

      <CardContent className="max-h-96 overflow-y-auto">
        <div className="space-y-2">
          {loading ? (
            <p className="text-center text-zinc-500 py-8">Loading trades...</p>
          ) : trades.length === 0 ? (
            <p className="text-center text-zinc-500 py-8">No trades yet</p>
          ) : (
            trades.map((trade, index) => (
              <div
                key={`${trade.id}-${index}`}
                className={`flex items-center justify-between p-3 rounded-lg bg-zinc-800/50
                           hover:bg-zinc-800 transition-colors
                           ${index === 0 ? 'animate-fade-in' : ''}`}
              >
                <div className="flex items-center gap-3">
                  {/* Side indicator */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm
                    ${trade.taker_side === 'buy'
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'
                    }`}>
                    {trade.taker_side === 'buy' ? '↗' : '↘'}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${
                        trade.taker_side === 'buy' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {formatNumber(trade.quantity, 4)} OLTIN
                      </span>
                      <span className="text-xs text-zinc-500">
                        @ ${formatNumber(trade.price, 2)}
                      </span>
                    </div>
                    <span className="text-xs text-zinc-500">
                      ${formatNumber(String(Number(trade.price) * Number(trade.quantity)), 2)} USD
                    </span>
                  </div>
                </div>

                <span className="text-xs text-zinc-500">
                  {formatTimeAgo(trade.created_at)}
                </span>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
