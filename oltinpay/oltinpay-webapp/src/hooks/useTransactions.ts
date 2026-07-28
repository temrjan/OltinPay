import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';

/**
 * On-chain transaction feed (GET /transactions, indexer-backed), newest first.
 * The backend returns 400 when the user has no registered wallet_address yet;
 * `retry: false` keeps that a terminal empty state rather than a retry storm.
 * Callers treat an error OR an empty list as "no on-chain activity" — an empty
 * state, not a failure toast.
 */
export function useTransactions() {
  return useQuery({
    queryKey: ['transactions'],
    queryFn: () => api.getTransactions(),
    staleTime: 30000,
    retry: false,
  });
}
