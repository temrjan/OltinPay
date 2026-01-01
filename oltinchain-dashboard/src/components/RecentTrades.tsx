"use client";

import { useState, useEffect, useRef } from "react";
import { logger } from "@/lib/logger";

interface Trade {
  id: string;
  price: string;
  quantity: string;
  taker_side: string;
  created_at: string;
}

export default function RecentTrades() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const WS_URL = API_URL.replace("http", "ws");

  useEffect(() => {
    mountedRef.current = true;

    const fetchTrades = async () => {
      try {
        const res = await fetch(`${API_URL}/orderbook/trades?limit=20`);
        if (res.ok && mountedRef.current) {
          const data = await res.json();
          setTrades(data.trades || []);
        }
      } catch (e) {
        logger.error("Failed to fetch trades:", e);
      }
    };

    fetchTrades();

    const connectWs = () => {
      if (!mountedRef.current) return;

      const ws = new WebSocket(`${WS_URL}/ws?channels=trades`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (mountedRef.current) {
          logger.log("Trades WS connected");
          setConnected(true);
        }
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const message = JSON.parse(event.data);
          if (message.type === "trade") {
            setTrades(prev => [message.data, ...prev.slice(0, 19)]);
          }
        } catch (e) {
          logger.error("WS parse error:", e);
        }
      };

      ws.onclose = () => {
        if (mountedRef.current) {
          logger.log("Trades WS disconnected");
          setConnected(false);
          setTimeout(connectWs, 5000);
        }
      };

      ws.onerror = (error) => {
        logger.error("WS error:", error);
      };
    };

    connectWs();

    const pollInterval = setInterval(() => {
      if (!connected) {
        fetchTrades();
      }
    }, 10000);

    return () => {
      mountedRef.current = false;
      clearInterval(pollInterval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [API_URL, WS_URL]);

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Recent Trades</h3>
        <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
      </div>

      <div className="space-y-2">
        <div className="grid grid-cols-4 text-xs text-zinc-500 font-medium">
          <span>Price</span>
          <span className="text-center">Amount</span>
          <span className="text-center">Total</span>
          <span className="text-right">Time</span>
        </div>

        <div className="space-y-1 max-h-[300px] overflow-y-auto">
          {trades.map((trade, i) => {
            const total = (parseFloat(trade.price) * parseFloat(trade.quantity)).toFixed(2);
            const isBuy = trade.taker_side === "buy";

            return (
              <div key={trade.id || i} className="grid grid-cols-4 text-sm">
                <span className={isBuy ? "text-green-400" : "text-red-400"}>
                  {parseFloat(trade.price).toFixed(2)}
                </span>
                <span className="text-center text-zinc-300">
                  {parseFloat(trade.quantity).toFixed(6)}
                </span>
                <span className="text-center text-zinc-400">
                  {total}
                </span>
                <span className="text-right text-zinc-500">
                  {formatTime(trade.created_at)}
                </span>
              </div>
            );
          })}
        </div>

        {trades.length === 0 && (
          <div className="text-center text-zinc-500 py-8">
            No trades yet
          </div>
        )}
      </div>
    </div>
  );
}
