'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './Card';
import { formatNumber } from '@/lib/utils';

import { createChart, AreaSeries, IChartApi, ISeriesApi, Time, AreaData } from 'lightweight-charts';

interface XauUsdPrice {
  price_usd: number;
  price_change_pct: number;
  data_index: number;
  data_date: string;
  timestamp: string;
}

interface HistoryPoint {
  timestamp: string;
  price_usd: number;
  change_pct: number;
}

type Timeframe = '1h' | '6h' | '1d' | '1w' | '1m' | 'all';

const TIMEFRAMES: { key: Timeframe; label: string; hours: number }[] = [
  { key: '1h', label: '1ч', hours: 1 },
  { key: '6h', label: '6ч', hours: 6 },
  { key: '1d', label: '1д', hours: 24 },
  { key: '1w', label: '1нед', hours: 24 * 7 },
  { key: '1m', label: '1мес', hours: 24 * 30 },
  { key: 'all', label: 'Всё', hours: 0 },
];

export function PriceChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const fullscreenContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);

  const [currentPrice, setCurrentPrice] = useState<XauUsdPrice | null>(null);
  const [loading, setLoading] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [timeframe, setTimeframe] = useState<Timeframe>('all');
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Fetch XAU/USD price
  const fetchPrice = useCallback(async () => {
    try {
      const response = await fetch(API_URL + '/price/xau-usd');
      if (response.ok) {
        const data = await response.json();
        if (data.price_usd > 0) {
          setCurrentPrice(data);
          setError(null);

          // Add new point to chart
          if (seriesRef.current && data.price_usd > 0) {
            const now = Math.floor(Date.now() / 1000) as Time;
            seriesRef.current.update({
              time: now,
              value: data.price_usd,
            });
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch XAU/USD price:', err);
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  // Fetch history for chart with timeframe filter
  const fetchHistory = useCallback(async () => {
    try {
      const response = await fetch(API_URL + '/price/xau-usd/history?limit=500');
      if (response.ok) {
        const data = await response.json();
        if (data.prices && data.prices.length > 0 && seriesRef.current) {
          let prices = data.prices;

          // Filter by timeframe
          if (timeframe !== 'all') {
            const tf = TIMEFRAMES.find(t => t.key === timeframe);
            if (tf && tf.hours > 0) {
              const cutoff = Date.now() - tf.hours * 60 * 60 * 1000;
              prices = prices.filter((p: HistoryPoint) =>
                new Date(p.timestamp).getTime() >= cutoff
              );
            }
          }

          const chartData: AreaData<Time>[] = prices
            .map((p: HistoryPoint) => ({
              time: Math.floor(new Date(p.timestamp).getTime() / 1000) as Time,
              value: p.price_usd,
            }))
            .filter((p: AreaData<Time>) => p.value > 0)
            .sort((a: AreaData<Time>, b: AreaData<Time>) => (a.time as number) - (b.time as number))
            .filter((p: AreaData<Time>, i: number, arr: AreaData<Time>[]) => 
              i === 0 || p.time !== arr[i - 1].time
            );

          if (chartData.length > 0) {
            seriesRef.current.setData(chartData);
            chartRef.current?.timeScale().fitContent();
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  }, [API_URL, timeframe]);

  // Poll for updates
  useEffect(() => {
    fetchPrice();
    const interval = setInterval(fetchPrice, 3000);
    return () => clearInterval(interval);
  }, [fetchPrice]);

  // Initialize chart
  useEffect(() => {
    const container = isFullscreen ? fullscreenContainerRef.current : chartContainerRef.current;
    if (!container) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      seriesRef.current = null;
    }

    const chart = createChart(container, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#a1a1aa',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      width: container.clientWidth,
      height: isFullscreen ? window.innerHeight - 120 : 300,
      timeScale: {
        borderColor: '#3f3f46',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#3f3f46',
      },
      crosshair: {
        vertLine: { color: '#fbbf24', labelBackgroundColor: '#fbbf24' },
        horzLine: { color: '#fbbf24', labelBackgroundColor: '#fbbf24' },
      },
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: '#fbbf24',
      topColor: 'rgba(251, 191, 36, 0.4)',
      bottomColor: 'rgba(251, 191, 36, 0.0)',
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = areaSeries;
    fetchHistory();

    const handleResize = () => {
      if (container && chartRef.current) {
        chartRef.current.applyOptions({
          width: container.clientWidth,
          height: isFullscreen ? window.innerHeight - 120 : 300,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
      }
    };
  }, [isFullscreen, fetchHistory]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen]);

  const toggleFullscreen = () => setIsFullscreen(!isFullscreen);

  const TimeframeButtons = () => (
    <div className="flex gap-1">
      {TIMEFRAMES.map((tf) => (
        <button
          key={tf.key}
          onClick={() => setTimeframe(tf.key)}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            timeframe === tf.key
              ? 'bg-amber-500 text-zinc-900 font-medium'
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          {tf.label}
        </button>
      ))}
    </div>
  );

  const chartContent = (
    <>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            XAU/USD (Gold Price)
            {currentPrice?.data_date && (
              <span className="text-sm font-normal text-zinc-500">
                Historical: {currentPrice.data_date}
              </span>
            )}
          </CardTitle>
          <div className="flex items-baseline gap-3 mt-2">
            <span className="text-3xl font-bold text-amber-400">
              {loading ? '...' : '$' + formatNumber(currentPrice?.price_usd || 0, 2)}
            </span>
            {currentPrice && (
              <span className={'text-sm font-medium ' + (
                currentPrice.price_change_pct >= 0 ? 'text-green-400' : 'text-red-400'
              )}>
                {currentPrice.price_change_pct >= 0 ? '+' : ''}
                {currentPrice.price_change_pct.toFixed(2)}%
              </span>
            )}
            {currentPrice?.data_index !== undefined && (
              <span className="text-xs text-zinc-500">
                Point #{currentPrice.data_index + 1}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <TimeframeButtons />
          <button
            onClick={toggleFullscreen}
            className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 transition-colors"
            title={isFullscreen ? 'Exit fullscreen (ESC)' : 'Fullscreen'}
          >
            {isFullscreen ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              </svg>
            )}
          </button>
        </div>
      </CardHeader>

      <CardContent>
        <div
          ref={isFullscreen ? fullscreenContainerRef : chartContainerRef}
          className="w-full"
        />

        {error && (
          <div className="text-red-400 text-sm mt-2">{error}</div>
        )}

        <div className="flex justify-between text-sm text-zinc-500 mt-4">
          <span>Replay Strategy: Historical XAU/USD</span>
          <span>
            Updated: {currentPrice?.timestamp
              ? new Date(currentPrice.timestamp).toLocaleTimeString()
              : '-'}
          </span>
        </div>
      </CardContent>
    </>
  );

  if (isFullscreen) {
    return (
      <div className="fixed inset-0 z-50 bg-zinc-950">
        <Card className="h-full rounded-none border-0">
          {chartContent}
        </Card>
      </div>
    );
  }

  return <Card>{chartContent}</Card>;
}
