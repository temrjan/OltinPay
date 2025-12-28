'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import type { WSMessage } from '@/types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'wss://api.oltinchain.com/ws';
const RECONNECT_DELAY = 3000;
const HEARTBEAT_INTERVAL = 30000;

interface UseWebSocketOptions {
  channels?: string[];
  onMessage?: (message: WSMessage) => void;
  autoConnect?: boolean;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WSMessage | null;
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
  sendMessage: (message: object) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { channels = ['price', 'metrics'], onMessage, autoConnect = true } = options;
  
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const channelParam = channels.join(',');
    const ws = new WebSocket(`${WS_URL}?channels=${channelParam}`);

    ws.onopen = () => {
      setIsConnected(true);
      console.log('[WS] Connected');
      
      // Start heartbeat
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, HEARTBEAT_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WSMessage;
        setLastMessage(message);
        onMessage?.(message);
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log('[WS] Disconnected');
      
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
      }

      // Auto reconnect
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('[WS] Reconnecting...');
        connect();
      }, RECONNECT_DELAY);
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
    };

    wsRef.current = ws;
  }, [channels, onMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
    }
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const subscribe = useCallback((channel: string) => {
    wsRef.current?.send(JSON.stringify({ type: 'subscribe', channel }));
  }, []);

  const unsubscribe = useCallback((channel: string) => {
    wsRef.current?.send(JSON.stringify({ type: 'unsubscribe', channel }));
  }, []);

  const sendMessage = useCallback((message: object) => {
    wsRef.current?.send(JSON.stringify(message));
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => disconnect();
  }, [autoConnect, connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    subscribe,
    unsubscribe,
    sendMessage,
  };
}
