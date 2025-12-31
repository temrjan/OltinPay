'use client';

import { useEffect, useState } from 'react';

interface MatchData {
  match_id: string;
  started_at: string;
  cycles_completed: number;
  current_leader: string;
  deviation: string;
  target_price: string;
  market_price: string;
}

interface LiveMatchWidgetProps {
  match: MatchData | null;
}

export function LiveMatchWidget({ match }: LiveMatchWidgetProps) {
  const [timeRemaining, setTimeRemaining] = useState<string>('--:--:--');
  
  useEffect(() => {
    const calculateTimeRemaining = () => {
      const now = new Date();
      const tashkentOffset = 5 * 60;
      const localOffset = now.getTimezoneOffset();
      const tashkentTime = new Date(now.getTime() + (tashkentOffset + localOffset) * 60000);
      
      const midnight = new Date(tashkentTime);
      midnight.setHours(24, 0, 0, 0);
      
      const diff = midnight.getTime() - tashkentTime.getTime();
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);
      
      setTimeRemaining(
        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
      );
    };
    
    calculateTimeRemaining();
    const interval = setInterval(calculateTimeRemaining, 1000);
    return () => clearInterval(interval);
  }, []);

  const deviation = match?.deviation ? parseFloat(match.deviation) : 0;
  const deviationPercent = deviation * 100;
  const leader = match?.current_leader || 'DRAW';
  const buyerProgress = Math.max(0, Math.min(100, 50 + deviationPercent * 5));
  
  const getLeaderInfo = () => {
    if (leader === 'BUYERS' || deviationPercent > 1) {
      return { icon: '🟢', color: 'text-green-400', label: 'BUYERS' };
    } else if (leader === 'SELLERS' || deviationPercent < -1) {
      return { icon: '🔴', color: 'text-red-400', label: 'SELLERS' };
    }
    return { icon: '⚪', color: 'text-gray-400', label: 'DRAW' };
  };
  
  const leaderInfo = getLeaderInfo();

  return (
    <div className="bg-gradient-to-br from-gray-800 via-gray-800 to-gray-900 rounded-xl p-4 sm:p-5 border border-gray-700 shadow-xl">
      {/* Header - Mobile optimized */}
      <div className="flex items-center justify-between mb-3 sm:mb-4">
        <h2 className="text-base sm:text-lg font-bold text-yellow-500 flex items-center gap-1 sm:gap-2">
          <span className="text-xl sm:text-2xl">⚔️</span> 
          <span className="hidden xs:inline">Live</span> Match
        </h2>
        <div className="flex items-center gap-1 sm:gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-green-400 text-xs">LIVE</span>
        </div>
      </div>

      {/* VS Banner - Compact on mobile */}
      <div className="flex justify-between items-center mb-4 sm:mb-6">
        <div className="text-center flex-1">
          <div className="text-2xl sm:text-3xl mb-1">🟢</div>
          <div className="text-green-400 font-bold text-sm sm:text-lg">BUYERS</div>
        </div>
        
        <div className="text-center px-2 sm:px-4">
          <div className="text-2xl sm:text-4xl font-black text-yellow-500">VS</div>
        </div>
        
        <div className="text-center flex-1">
          <div className="text-2xl sm:text-3xl mb-1">🔴</div>
          <div className="text-red-400 font-bold text-sm sm:text-lg">SELLERS</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4 sm:mb-6">
        <div className="relative h-6 sm:h-8 bg-gray-700 rounded-full overflow-hidden">
          <div 
            className="absolute left-0 top-0 h-full bg-gradient-to-r from-green-600 to-green-500 transition-all duration-500"
            style={{ width: `${buyerProgress}%` }}
          />
          <div 
            className="absolute right-0 top-0 h-full bg-gradient-to-l from-red-600 to-red-500 transition-all duration-500"
            style={{ width: `${100 - buyerProgress}%` }}
          />
          <div className="absolute left-1/2 top-0 w-0.5 sm:w-1 h-full bg-yellow-400 transform -translate-x-1/2 z-10" />
          <div 
            className="absolute top-1/2 w-3 h-3 sm:w-4 sm:h-4 bg-yellow-400 rounded-full border-2 border-white transform -translate-y-1/2 z-20 shadow-lg transition-all duration-500"
            style={{ left: `calc(${buyerProgress}% - 6px)` }}
          />
        </div>
      </div>

      {/* Leader Display - Compact on mobile */}
      <div className="text-center mb-4 sm:mb-6 py-3 sm:py-4 bg-gray-700/50 rounded-lg">
        <div className="text-xs sm:text-sm text-gray-400 mb-1">Current Leader</div>
        <div className={`text-xl sm:text-3xl font-black ${leaderInfo.color} flex items-center justify-center gap-1 sm:gap-2`}>
          <span>{leaderInfo.icon}</span>
          <span>{leaderInfo.label}</span>
        </div>
        <div className={`text-sm sm:text-lg font-bold ${deviationPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {deviationPercent >= 0 ? '+' : ''}{deviationPercent.toFixed(2)}%
        </div>
      </div>

      {/* Stats Grid - 2 columns on mobile */}
      <div className="grid grid-cols-2 gap-2 sm:gap-4 mb-4 sm:mb-6">
        <div className="bg-gray-700/30 rounded-lg p-2 sm:p-3 text-center">
          <div className="text-[10px] sm:text-xs text-gray-400">Market</div>
          <div className="text-base sm:text-xl font-bold text-white">
            ${parseFloat(match?.market_price || '0').toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-700/30 rounded-lg p-2 sm:p-3 text-center">
          <div className="text-[10px] sm:text-xs text-gray-400">Target</div>
          <div className="text-base sm:text-xl font-bold text-yellow-400">
            ${parseFloat(match?.target_price || '0').toFixed(2)}
          </div>
        </div>
      </div>

      {/* Countdown Timer */}
      <div className="bg-gray-900 rounded-lg p-3 sm:p-4 text-center">
        <div className="text-[10px] sm:text-xs text-gray-400 mb-1 sm:mb-2">⏱️ Match Ends In</div>
        <div className="text-2xl sm:text-3xl font-mono font-bold text-yellow-400">
          {timeRemaining}
        </div>
      </div>

      {/* Cycles Counter */}
      <div className="mt-3 sm:mt-4 text-center text-xs sm:text-sm text-gray-400">
        Cycles: <span className="text-white font-bold">{match?.cycles_completed || 0}</span>
      </div>
    </div>
  );
}
