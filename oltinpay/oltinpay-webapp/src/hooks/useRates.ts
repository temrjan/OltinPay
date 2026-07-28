import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';

/**
 * Live OLTIN price from GET /rates (public, feed-derived). `oltin_price_uzd` is
 * UZS per 1 OLTIN — the real on-chain price, kept fresh by the feed keeper
 * (Block K). Refetched every 30s.
 */
export function useRates() {
  return useQuery({
    queryKey: ['rates'],
    queryFn: () => api.getRates(),
    staleTime: 30000,
    refetchInterval: 30000,
  });
}
