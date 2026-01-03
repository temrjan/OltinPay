'use client';

import { useState, useEffect } from 'react';

interface PriceData {
  price: string;
  bid: string;
  ask: string;
  spread_percent: string;
}

interface CycleData {
  cycle_number: number;
  phase: string;
  day_in_cycle: number;
  cycle_progress: number;
  current_price: string;
  peak_price: string;
  bottom_price: string;
}

type OrderSide = 'buy' | 'sell';
type OrderType = 'market' | 'limit';

const DEMO_USD_BALANCE = 1000;

export default function TradingWidget() {
  const [price, setPrice] = useState<PriceData | null>(null);
  const [cycle, setCycle] = useState<CycleData | null>(null);
  const [side, setSide] = useState<OrderSide>('buy');
  const [orderType, setOrderType] = useState<OrderType>('market');
  const [amount, setAmount] = useState('');
  const [limitPrice, setLimitPrice] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchPrice = async () => {
      try {
        const [priceRes, cycleRes] = await Promise.all([
          fetch(`${API_URL}/price/current`),
          fetch(`${API_URL}/price/cycle`),
        ]);
        if (priceRes.ok) setPrice(await priceRes.json());
        if (cycleRes.ok) setCycle(await cycleRes.json());
      } catch (e) {
        console.error('Failed to fetch price:', e);
      }
    };

    fetchPrice();
    const interval = setInterval(fetchPrice, 5000);
    return () => clearInterval(interval);
  }, [API_URL]);

  useEffect(() => {
    if (price && !limitPrice) {
      setLimitPrice(price.price);
    }
  }, [price, limitPrice]);

  // Calculate OLTIN equivalent from demo balance
  const oltinBalance = price ? (DEMO_USD_BALANCE / parseFloat(price.price)).toFixed(4) : '---';

  const getEstimate = () => {
    if (!amount || !price) return null;
    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum <= 0) return null;

    if (side === 'buy') {
      const askPrice = parseFloat(price.ask);
      const fee = Math.max(amountNum * 0.015, 1);
      const net = amountNum - fee;
      const oltin = net / askPrice;
      return { oltin: oltin.toFixed(6), fee: fee.toFixed(2) };
    } else {
      const bidPrice = parseFloat(price.bid);
      const gross = amountNum * bidPrice;
      const fee = Math.max(gross * 0.015, 1);
      const net = gross - fee;
      return { usd: net.toFixed(2), fee: fee.toFixed(2) };
    }
  };

  const handleSubmit = async () => {
    if (!amount || loading) return;

    setLoading(true);
    setMessage(null);

    try {
      if (orderType === 'limit') {
        const orderPrice = parseFloat(limitPrice || price?.price || '0');
        const quantity = parseFloat(amount);

        if (isNaN(orderPrice) || orderPrice <= 0 || isNaN(quantity) || quantity <= 0) {
          setMessage({ type: 'error', text: 'Введите корректные данные' });
          return;
        }

        const res = await fetch(`${API_URL}/orderbook/orders`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            side,
            price: orderPrice.toFixed(2),
            quantity: quantity.toFixed(8),
          }),
        });

        if (res.ok) {
          const data = await res.json();
          setMessage({ type: 'success', text: data.message || 'Ордер размещен успешно' });
          setAmount('');
        } else {
          const err = await res.json();
          setMessage({ type: 'error', text: err.detail || 'Ошибка при размещении ордера' });
        }
      } else {
        const endpoint = side === 'buy' ? '/orders/buy' : '/orders/sell';
        const res = await fetch(`${API_URL}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount: parseFloat(amount) }),
        });

        if (res.ok) {
          setMessage({ type: 'success', text: 'Ордер выполнен успешно' });
          setAmount('');
        } else {
          const err = await res.json();
          setMessage({ type: 'error', text: err.detail || 'Ошибка при выполнении ордера' });
        }
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Ошибка сети' });
    } finally {
      setLoading(false);
    }
  };

  const estimate = getEstimate();

  const phaseColors: Record<string, string> = {
    accumulation: 'text-yellow-500',
    markup: 'text-green-500',
    distribution: 'text-orange-500',
    markdown: 'text-red-500',
    capitulation: 'text-red-600',
    re_accumulation: 'text-emerald-500',
  };

  const phaseLabels: Record<string, string> = {
    accumulation: 'Накопление',
    markup: 'Рост',
    distribution: 'Распределение',
    markdown: 'Падение',
    capitulation: 'Капитуляция',
    re_accumulation: 'Ре-аккумуляция',
  };

  return (
    <div className="bg-[#111] border border-[#222] rounded-xl p-6 max-w-md w-full">
      {/* Demo Balance Card */}
      <div className="bg-gradient-to-r from-[#1a1a1a] to-[#0d0d0d] border border-[#333] rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[#888] text-sm">Демо-баланс</span>
          <span className="text-xs px-2 py-1 bg-[#D4AF37]/20 text-[#D4AF37] rounded-full">Demo</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[#666] text-xs mb-1">USD</p>
            <p className="text-white text-xl font-bold">${DEMO_USD_BALANCE.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-[#666] text-xs mb-1">OLTIN</p>
            <p className="text-[#D4AF37] text-xl font-bold">{oltinBalance}</p>
          </div>
        </div>
      </div>

      {/* Header with price */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[#888] text-sm">OLTIN/USD</span>
          {cycle && (
            <span className={`text-xs px-2 py-1 rounded-full bg-[#1a1a1a] ${phaseColors[cycle.phase] || 'text-gray-400'}`}>
              {phaseLabels[cycle.phase] || cycle.phase}
            </span>
          )}
        </div>
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-white">
            ${price?.price || '---'}
          </span>
          {cycle && (
            <span className="text-sm text-[#888]">
              Цикл {cycle.cycle_number} • День {cycle.day_in_cycle.toFixed(1)}
            </span>
          )}
        </div>
        <div className="flex gap-4 mt-2 text-sm">
          <span className="text-green-500">Bid: ${price?.bid || '---'}</span>
          <span className="text-red-500">Ask: ${price?.ask || '---'}</span>
        </div>
      </div>

      {/* Cycle progress */}
      {cycle && (
        <div className="mb-6">
          <div className="flex justify-between text-xs text-[#888] mb-1">
            <span>Прогресс цикла</span>
            <span>{(cycle.cycle_progress * 100).toFixed(0)}%</span>
          </div>
          <div className="h-2 bg-[#222] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#D4AF37] to-[#F4D03F] transition-all duration-500"
              style={{ width: `${cycle.cycle_progress * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-[#666] mt-1">
            <span>Дно: ${cycle.bottom_price}</span>
            <span>Пик: ${cycle.peak_price}</span>
          </div>
        </div>
      )}

      {/* Buy/Sell tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setSide('buy')}
          className={`flex-1 py-3 rounded-lg font-medium transition-all ${
            side === 'buy'
              ? 'bg-green-600 text-white'
              : 'bg-[#1a1a1a] text-[#888] hover:bg-[#222]'
          }`}
        >
          Купить
        </button>
        <button
          onClick={() => setSide('sell')}
          className={`flex-1 py-3 rounded-lg font-medium transition-all ${
            side === 'sell'
              ? 'bg-red-600 text-white'
              : 'bg-[#1a1a1a] text-[#888] hover:bg-[#222]'
          }`}
        >
          Продать
        </button>
      </div>

      {/* Order type */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setOrderType('market')}
          className={`px-4 py-2 rounded-lg text-sm transition-all ${
            orderType === 'market'
              ? 'bg-[#D4AF37] text-black'
              : 'bg-[#1a1a1a] text-[#888] hover:bg-[#222]'
          }`}
        >
          Market
        </button>
        <button
          onClick={() => setOrderType('limit')}
          className={`px-4 py-2 rounded-lg text-sm transition-all ${
            orderType === 'limit'
              ? 'bg-[#D4AF37] text-black'
              : 'bg-[#1a1a1a] text-[#888] hover:bg-[#222]'
          }`}
        >
          Limit
        </button>
      </div>

      {/* Amount input */}
      <div className="mb-4">
        <label className="block text-[#888] text-sm mb-2">
          {orderType === 'limit' ? 'Количество (OLTIN)' : (side === 'buy' ? 'Сумма (USD)' : 'Количество (OLTIN)')}
        </label>
        <div className="relative">
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            className="w-full bg-[#1a1a1a] border border-[#333] rounded-lg px-4 py-3 text-white text-lg focus:outline-none focus:border-[#D4AF37] transition-colors"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[#666]">
            {orderType === 'limit' ? 'OLTIN' : (side === 'buy' ? 'USD' : 'OLTIN')}
          </span>
        </div>
      </div>

      {/* Limit price input */}
      {orderType === 'limit' && (
        <div className="mb-4">
          <label className="block text-[#888] text-sm mb-2">Цена (USD)</label>
          <input
            type="number"
            value={limitPrice}
            onChange={(e) => setLimitPrice(e.target.value)}
            placeholder={price?.price || '0.00'}
            className="w-full bg-[#1a1a1a] border border-[#333] rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#D4AF37] transition-colors"
          />
        </div>
      )}

      {/* Estimate */}
      {estimate && orderType === 'market' && (
        <div className="bg-[#1a1a1a] rounded-lg p-4 mb-4">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-[#888]">Вы получите</span>
            <span className="text-white font-medium">
              {side === 'buy' ? `${estimate.oltin} OLTIN` : `$${estimate.usd}`}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-[#888]">Комиссия (1.5%)</span>
            <span className="text-[#666]">${estimate.fee}</span>
          </div>
        </div>
      )}

      {/* Limit order estimate */}
      {orderType === 'limit' && amount && limitPrice && (
        <div className="bg-[#1a1a1a] rounded-lg p-4 mb-4">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-[#888]">Всего</span>
            <span className="text-white font-medium">
              ${(parseFloat(amount) * parseFloat(limitPrice)).toFixed(2)} USD
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-[#888]">Тип</span>
            <span className="text-[#666]">Лимитный ордер</span>
          </div>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className={`rounded-lg p-3 mb-4 text-sm ${
          message.type === 'success' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
        }`}>
          {message.text}
        </div>
      )}

      {/* Submit button */}
      <button
        onClick={handleSubmit}
        disabled={!amount || loading}
        className={`w-full py-4 rounded-lg font-bold text-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
          side === 'buy'
            ? 'bg-green-600 hover:bg-green-500 text-white'
            : 'bg-red-600 hover:bg-red-500 text-white'
        }`}
      >
        {loading ? 'Обработка...' : side === 'buy' ? 'Купить OLTIN' : 'Продать OLTIN'}
      </button>

      <p className="text-center text-[#666] text-xs mt-4">
        {orderType === 'limit'
          ? 'Лимитный ордер будет исполнен когда цена достигнет указанного уровня'
          : 'Цена обновляется каждые 5 секунд. Комиссия: 1.5% (мин. $1)'
        }
      </p>
    </div>
  );
}
