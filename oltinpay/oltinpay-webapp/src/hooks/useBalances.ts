import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';

/**
 * Single source of truth for the on-chain balances (GET /balances). The wallet
 * and send screens both read through this hook so the parsing lives in ONE place
 * (do not re-query per screen). Returns raw wei strings — format for display via
 * lib/format.formatToken. The `['balances']` query key is invalidated by the
 * welcome claim mutation, giving read-after-write for free.
 */
export function useBalances() {
  return useQuery({
    queryKey: ['balances'],
    queryFn: () => api.getBalances(),
    staleTime: 30000,
  });
}
