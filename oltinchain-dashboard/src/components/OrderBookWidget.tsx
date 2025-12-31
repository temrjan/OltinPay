'use client';

import { useState, useEffect, useRef } from 'react';

interface OrderLevel {
  price: string;
  quantity: string;
}

interface OrderBookData {
  bids: OrderLevel[];
  asks: OrderLevel[];
}

interface Props {
  depth?: number;
}

export default function OrderBookWidget({ depth = 10 }: Props) {
  const [orderbook, setOrderbook] = useState<OrderBookData | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const WS_URL = API_URL.replace('http', 'ws');

  useEffect(() => {
    mountedRef.current = true;

    // Fetch initial orderbook
    const fetchOrderbook = async () => {
      try {
        const res = await fetch(`${API_URL}/orderbook?depth=${depth}`);
        if (res.ok && mountedRef.current) {
          setOrderbook(await res.json());
        }
      } catch (e) {
        console.error('Failed to fetch orderbook:', e);
      }
    };

    fetchOrderbook();

    // Connect WebSocket
    const connectWs = () => {
      if (!mountedRef.current) return;
      
      const ws = new WebSocket(`${WS_URL}/ws?channels=orderbook`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (mountedRef.current) {
          console.log('OrderBook WS connected');
          setConnected(true);
        }
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'orderbook') {
            setOrderbook(message.data);
          }
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };

      ws.onclose = () => {
        if (mountedRef.current) {
          console.log('OrderBook WS disconnected');
          setConnected(false);
          // Reconnect after 5 seconds
          setTimeout(connectWs, 5000);
        }
      };

      ws.onerror = (error) => {
        console.error('WS error:', error);
      };
    };

    connectWs();

    // Polling fallback
    const pollInterval = setInterval(() => {
      if (!connected) {
        fetchOrderbook();
      }
    }, 5000);

    return () => {
      mountedRef.current = false;
      clearInterval(pollInterval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [API_URL, WS_URL, depth]);

  const calculateTotal = (price: string, quantity: string) => {
    const p = parseFloat(price) || 0;
    const q = parseFloat(quantity) || 0;
    return (p * q).toFixed(2);
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Order Book</h3>
        <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
      </div>

      <div className="space-y-4">
        {/* Header */}
        <div className="grid grid-cols-3 text-xs text-zinc-500 font-medium">
          <span>Price (USD)</span>
          <span className="text-center">Amount (OLTIN)</span>
          <span className="text-right">Total (USD)</span>
        </div>

        {/* Asks (sells) - red */}
        <div className="space-y-1">
          {orderbook?.asks?.slice().reverse().map((ask, i) => (
            <div key={`ask-${i}`} className="grid grid-cols-3 text-sm">
              <span className="text-red-400">{parseFloat(ask.price).toFixed(2)}</span>
              <span className="text-center text-zinc-300">{parseFloat(ask.quantity).toFixed(6)}</span>
              <span className="text-right text-zinc-400">{calculateTotal(ask.price, ask.quantity)}</span>
            </div>
          ))}
        </div>

        {/* Spread indicator */}
        {orderbook?.asks?.[0] && orderbook?.bids?.[0] && (
          <div className="text-center text-xs text-zinc-500 py-2 border-y border-zinc-800">
            Spread: ${(parseFloat(orderbook.asks[0].price) - parseFloat(orderbook.bids[0].price)).toFixed(2)}
          </div>
        )}

        {/* Bids (buys) - green */}
        <div className="space-y-1">
          {orderbook?.bids?.map((bid, i) => (
            <div key={`bid-${i}`} className="grid grid-cols-3 text-sm">
              <span className="text-green-400">{parseFloat(bid.price).toFixed(2)}</span>
              <span className="text-center text-zinc-300">{parseFloat(bid.quantity).toFixed(6)}</span>
              <span className="text-right text-zinc-400">{calculateTotal(bid.price, bid.quantity)}</span>
            </div>
          ))}
        </div>

        {/* Empty state */}
        {(!orderbook?.bids?.length && !orderbook?.asks?.length) && (
          <div className="text-center text-zinc-500 py-8">
            No orders in book
          </div>
        )}
      </div>
    </div>
  );
}
