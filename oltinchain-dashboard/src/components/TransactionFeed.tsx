'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './Card';
import { useWebSocket } from '@/hooks/useWebSocket';
import { formatNumber, formatAddress, formatTimeAgo } from '@/lib/utils';

interface Transaction {
  txHash: string;
  type: 'mint' | 'burn';
  address: string;
  amount: string;
  timestamp: string;
}

interface TransactionData {
  tx_hash: string;
  tx_type: 'mint' | 'burn';
  address: string;
  amount: string;
  timestamp: string;
}

export function TransactionFeed() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const { isConnected, lastMessage } = useWebSocket({
    channels: ['transactions'],
  });

  // Handle new transactions
  useEffect(() => {
    if (lastMessage?.type === 'transaction') {
      const msg = lastMessage as { type: string; data: TransactionData };
      const data = msg.data;
      const newTx: Transaction = {
        txHash: data.tx_hash,
        type: data.tx_type,
        address: data.address,
        amount: data.amount,
        timestamp: data.timestamp,
      };

      setTransactions((prev) => [newTx, ...prev].slice(0, 50));
    }
  }, [lastMessage]);

  // Generate some mock transactions for initial display
  useEffect(() => {
    if (transactions.length === 0) {
      const mockTxs: Transaction[] = [];
      const types: ('mint' | 'burn')[] = ['mint', 'burn'];
      
      for (let i = 0; i < 10; i++) {
        mockTxs.push({
          txHash: `0x${Math.random().toString(16).slice(2, 10)}....${Math.random().toString(16).slice(2, 6)}`,
          type: types[Math.floor(Math.random() * 2)],
          address: `0x${Math.random().toString(16).slice(2, 10)}...${Math.random().toString(16).slice(2, 6)}`,
          amount: (Math.random() * 10).toFixed(4),
          timestamp: new Date(Date.now() - i * 60000 * Math.random() * 10).toISOString(),
        });
      }
      setTransactions(mockTxs);
    }
  }, [transactions.length]);

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Live Transactions</CardTitle>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-xs text-zinc-500">
            {isConnected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </CardHeader>
      
      <CardContent className="max-h-96 overflow-y-auto">
        <div className="space-y-2">
          {transactions.length === 0 ? (
            <p className="text-center text-zinc-500 py-8">
              Waiting for transactions...
            </p>
          ) : (
            transactions.map((tx, index) => (
              <div
                key={`${tx.txHash}-${index}`}
                className={`flex items-center justify-between p-3 rounded-lg bg-zinc-800/50 
                           hover:bg-zinc-800 transition-colors
                           ${index === 0 ? 'animate-fade-in' : ''}`}
              >
                <div className="flex items-center gap-3">
                  {/* Type indicator */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm
                    ${tx.type === 'mint' 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-red-500/20 text-red-400'
                    }`}>
                    {tx.type === 'mint' ? '↗' : '↘'}
                  </div>
                  
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${
                        tx.type === 'mint' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {tx.type === 'mint' ? '+' : '-'}{formatNumber(tx.amount, 4)} OLTIN
                      </span>
                    </div>
                    <span className="text-xs text-zinc-500 font-mono">
                      {formatAddress(tx.address)}
                    </span>
                  </div>
                </div>
                
                <span className="text-xs text-zinc-500">
                  {formatTimeAgo(tx.timestamp)}
                </span>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
