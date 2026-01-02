const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.oltinchain.com';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export interface DashboardMetrics {
  total_supply: string;
  transaction_count_24h: number;
  active_users_24h: number;
  volume_24h: string;
}

export const api = {
  // Dashboard metrics
  getDashboardMetrics: () =>
    fetchAPI<DashboardMetrics>('/metrics/dashboard'),

  // Reserves
  getProofOfReserves: () =>
    fetchAPI<import('@/types').ProofOfReserves>('/reserves/proof'),

  getGoldBars: (limit = 50, offset = 0) =>
    fetchAPI<import('@/types').GoldBarListResponse>(`/reserves/bars?limit=${limit}&offset=${offset}`),

  lookupGoldBar: (serial: string) =>
    fetchAPI<import('@/types').GoldBar>(`/reserves/lookup?serial=${encodeURIComponent(serial)}`),

  // Price
  getGoldPrice: () =>
    fetchAPI<import('@/types').GoldPrice>('/price/gold'),

  // Blockchain
  getTokenInfo: () =>
    fetchAPI<import('@/types').TokenInfo>('/blockchain/token'),

  // WebSocket stats
  getWSStats: () =>
    fetchAPI<{ total_connections: number; users_connected: number; channels: Record<string, number> }>('/ws/stats'),
};
