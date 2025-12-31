'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, IChartApi, ISeriesApi, AreaData, Time, AreaSeries } from 'lightweight-charts';

interface HistoryItem {
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
}

interface HistoryResponse {
  interval: string;
  data: HistoryItem[];
}

type Interval = '1m' | '5m' | '15m' | '1h' | '4h' | '1d';

const INTERVALS: { key: Interval; label: string }[] = [
  { key: '1m', label: '1м' },
  { key: '5m', label: '5м' },
  { key: '15m', label: '15м' },
  { key: '1h', label: '1ч' },
  { key: '4h', label: '4ч' },
  { key: '1d', label: '1д' },
];

export default function OltinPriceChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  
  const [interval, setIntervalState] = useState<Interval>('1h');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/price/history?interval=${interval}&limit=100`);
      if (!res.ok) throw new Error('Failed to fetch history');
      
      const data: HistoryResponse = await res.json();
      
      const areaData: AreaData[] = data.data.map((item) => ({
        time: (new Date(item.timestamp).getTime() / 1000) as Time,
        value: parseFloat(item.close),
      }));

      if (seriesRef.current) {
        seriesRef.current.setData(areaData);
      }
      
      setError(null);
    } catch (e) {
      console.error('Failed to fetch history:', e);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  }, [API_URL, interval]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#111111' },
        textColor: '#888888',
      },
      grid: {
        vertLines: { color: '#222222' },
        horzLines: { color: '#222222' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 350,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: '#222222',
      },
      rightPriceScale: {
        borderColor: '#222222',
      },
      crosshair: {
        mode: 1,
        vertLine: { color: '#D4AF37', width: 1, style: 2 },
        horzLine: { color: '#D4AF37', width: 1, style: 2 },
      },
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: '#D4AF37',
      topColor: 'rgba(212, 175, 55, 0.4)',
      bottomColor: 'rgba(212, 175, 55, 0.0)',
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    fetchHistory();
    const intervalId = window.setInterval(fetchHistory, 30000);
    return () => clearInterval(intervalId);
  }, [fetchHistory]);

  return (
    <div className="w-full">
      <div className="flex gap-2 mb-4">
        {INTERVALS.map((i) => (
          <button
            key={i.key}
            onClick={() => setIntervalState(i.key)}
            className={`px-3 py-1 rounded text-sm transition-all ${
              interval === i.key
                ? 'bg-[#D4AF37] text-black'
                : 'bg-[#1a1a1a] text-[#888] hover:bg-[#222]'
            }`}
          >
            {i.label}
          </button>
        ))}
      </div>

      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#111]/80 z-10">
            <div className="w-6 h-6 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#111]/80 z-10">
            <p className="text-red-500">{error}</p>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full" />
      </div>
    </div>
  );
}
