// API Response Types

export interface ProofOfReserves {
  physical_gold: {
    total_grams: string;
    total_bars: number;
  };
  token_supply: {
    total_supply: string;
    contract_address: string | null;
  };
  coverage: {
    ratio: string;
    percentage: string;
    status: 'fully_backed' | 'nearly_backed' | 'under_backed';
  };
  verified_at: string;
}

export interface GoldBar {
  id: string;
  serial_number: string;
  weight_grams: number;
  purity: number;
  vault_location: string | null;
  acquired_at: string | null;
  status: string;
  created_at: string;
}

export interface GoldBarListResponse {
  bars: GoldBar[];
  total: number;
  limit: number;
  offset: number;
}

export interface GoldPrice {
  price_per_gram_uzs: number;
  price_per_gram_usd: number;
  updated_at: string;
}

export interface TokenInfo {
  name: string;
  symbol: string;
  total_supply: string;
  decimals: number;
  contract_address: string;
}

// WebSocket Message Types

export interface WSMessage {
  type: string;
  [key: string]: unknown;
}

export interface WSMetrics {
  type: 'metrics';
  data: {
    total_supply: string;
    transaction_count_24h: number;
    active_users_24h: number;
    volume_24h: string;
  };
}

export interface WSPrice {
  type: 'price';
  data: {
    price_uzs: number;
    price_usd: number;
    change_24h: number;
    timestamp: string;
  };
}

export interface WSTransaction {
  type: 'transaction';
  data: {
    tx_hash: string;
    tx_type: 'mint' | 'burn';
    address: string;
    amount: string;
    timestamp: string;
  };
}

// UI Types

export interface MetricCard {
  label: string;
  value: string;
  change?: number;
  icon?: string;
}
