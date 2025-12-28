'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './Card';
import { api } from '@/services/api';
import { formatNumber } from '@/lib/utils';
import type { ProofOfReserves as ProofOfReservesType } from '@/types';

export function ProofOfReserves() {
  const [proof, setProof] = useState<ProofOfReservesType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProof() {
      try {
        const data = await api.getProofOfReserves();
        setProof(data);
      } catch (err) {
        setError('Failed to fetch proof of reserves');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchProof();
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchProof, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card className="animate-pulse">
        <div className="h-48 bg-zinc-800 rounded-lg" />
      </Card>
    );
  }

  if (error || !proof) {
    return (
      <Card>
        <CardContent>
          <p className="text-red-400">{error || 'No data available'}</p>
        </CardContent>
      </Card>
    );
  }

  const physicalGold = parseFloat(proof.physical_gold.total_grams);
  const tokenSupply = parseFloat(proof.token_supply.total_supply);
  const coveragePercent = parseFloat(proof.coverage.percentage);

  const statusColors = {
    fully_backed: 'text-green-400',
    nearly_backed: 'text-yellow-400',
    under_backed: 'text-red-400',
  };

  const statusLabels = {
    fully_backed: 'Fully Backed ✓',
    nearly_backed: 'Nearly Backed',
    under_backed: 'Under Backed ⚠',
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Proof of Reserves</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Coverage Status */}
          <div className="text-center">
            <p className={`text-3xl font-bold ${statusColors[proof.coverage.status]}`}>
              {coveragePercent.toFixed(2)}%
            </p>
            <p className={`text-sm ${statusColors[proof.coverage.status]}`}>
              {statusLabels[proof.coverage.status]}
            </p>
          </div>

          {/* Comparison Bars */}
          <div className="space-y-4">
            {/* Physical Gold */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-zinc-400">Physical Gold</span>
                <span className="text-amber-400 font-medium">
                  {formatNumber(physicalGold, 4)} g
                </span>
              </div>
              <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-amber-500 to-amber-400 rounded-full"
                  style={{ width: `${Math.min(100, (physicalGold / Math.max(physicalGold, tokenSupply)) * 100)}%` }}
                />
              </div>
            </div>

            {/* Token Supply */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-zinc-400">Token Supply</span>
                <span className="text-blue-400 font-medium">
                  {formatNumber(tokenSupply, 4)} OLTIN
                </span>
              </div>
              <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full"
                  style={{ width: `${Math.min(100, (tokenSupply / Math.max(physicalGold, tokenSupply)) * 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-zinc-800">
            <div>
              <p className="text-xs text-zinc-500">Gold Bars</p>
              <p className="text-lg font-semibold text-zinc-200">{proof.physical_gold.total_bars}</p>
            </div>
            <div>
              <p className="text-xs text-zinc-500">Coverage Ratio</p>
              <p className="text-lg font-semibold text-zinc-200">{proof.coverage.ratio}</p>
            </div>
          </div>

          {/* Verified timestamp */}
          <p className="text-xs text-zinc-500 text-center">
            Verified: {new Date(proof.verified_at).toLocaleString()}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
