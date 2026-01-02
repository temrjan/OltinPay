'use client';

import { useEffect, useState } from 'react';
import { Card } from './Card';
import { useWebSocket } from '@/hooks/useWebSocket';
import { api } from '@/services/api';
import { formatNumber } from '@/lib/utils';

interface Metrics {
  totalSupply: string;
  transactionCount24h: number;
  activeUsers24h: number;
  volume24h: string;
}

export function LiveMetrics() {
  const [metrics, setMetrics] = useState<Metrics>({
    totalSupply: '0',
    transactionCount24h: 0,
    activeUsers24h: 0,
    volume24h: '0',
  });
  const [loading, setLoading] = useState(true);

  const { isConnected } = useWebSocket({
    channels: ['metrics'],
  });

  // Fetch metrics data
  useEffect(() => {
    async function fetchMetrics() {
      try {
        const data = await api.getDashboardMetrics();
        setMetrics({
          totalSupply: data.total_supply,
          transactionCount24h: data.transaction_count_24h,
          activeUsers24h: data.active_users_24h,
          volume24h: data.volume_24h,
        });
      } catch (error) {
        console.error('Failed to fetch metrics:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchMetrics();

    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const metricCards = [
    {
      label: 'Total Supply',
      value: `${formatNumber(metrics.totalSupply, 4)} OLTIN`,
      icon: '🪙',
    },
    {
      label: 'Transactions (24h)',
      value: formatNumber(metrics.transactionCount24h, 0),
      icon: '📊',
    },
    {
      label: 'Active Users (24h)',
      value: formatNumber(metrics.activeUsers24h, 0),
      icon: '👥',
    },
    {
      label: 'Volume (24h)',
      value: `${formatNumber(metrics.volume24h, 2)} OLTIN`,
      icon: '📈',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {metricCards.map((metric, index) => (
        <Card key={index} className="relative overflow-hidden">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-zinc-400 mb-1">{metric.label}</p>
              <p className="text-2xl font-bold text-zinc-100">
                {loading ? '...' : metric.value}
              </p>
            </div>
            <span className="text-2xl">{metric.icon}</span>
          </div>

          {/* Connection indicator */}
          <div className="absolute top-2 right-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          </div>
        </Card>
      ))}
    </div>
  );
}
