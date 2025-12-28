'use client';

import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './Card';
import { api } from '@/services/api';
import { formatNumber } from '@/lib/utils';
import type { GoldBar } from '@/types';

export function GoldBarLookup() {
  const [serial, setSerial] = useState('');
  const [bar, setBar] = useState<GoldBar | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!serial.trim()) return;

    setLoading(true);
    setError(null);
    setBar(null);
    setSearched(true);

    try {
      const data = await api.lookupGoldBar(serial.trim());
      setBar(data);
    } catch (err) {
      setError('Gold bar not found');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Gold Bar Lookup</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSearch} className="flex gap-2 mb-4">
          <input
            type="text"
            value={serial}
            onChange={(e) => setSerial(e.target.value)}
            placeholder="Enter serial number..."
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-zinc-100 
                       placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500"
          />
          <button
            type="submit"
            disabled={loading || !serial.trim()}
            className="bg-amber-500 hover:bg-amber-600 disabled:bg-zinc-700 disabled:cursor-not-allowed
                       text-black font-medium px-4 py-2 rounded-lg transition-colors"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && searched && (
          <div className="text-center py-8">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {bar && (
          <div className="bg-zinc-800/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-amber-400 font-mono text-lg">{bar.serial_number}</span>
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                bar.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-zinc-600/20 text-zinc-400'
              }`}>
                {bar.status.toUpperCase()}
              </span>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-zinc-500">Weight</p>
                <p className="text-zinc-200 font-medium">{formatNumber(bar.weight_grams, 4)} g</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500">Purity</p>
                <p className="text-zinc-200 font-medium">{bar.purity}‰</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500">Vault Location</p>
                <p className="text-zinc-200 font-medium">{bar.vault_location || 'N/A'}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500">Acquired</p>
                <p className="text-zinc-200 font-medium">
                  {bar.acquired_at ? new Date(bar.acquired_at).toLocaleDateString() : 'N/A'}
                </p>
              </div>
            </div>
          </div>
        )}

        {!bar && !error && searched && !loading && (
          <div className="text-center py-8">
            <p className="text-zinc-400">No results found</p>
          </div>
        )}

        {!searched && (
          <div className="text-center py-8">
            <p className="text-zinc-500 text-sm">
              Enter a gold bar serial number to verify its existence in reserves
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
