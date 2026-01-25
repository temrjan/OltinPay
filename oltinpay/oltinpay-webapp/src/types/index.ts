// API Types

export interface User {
  id: string;
  telegram_id: number;
  oltin_id: string;
  language: 'uz' | 'ru';
  created_at: string;
}

export interface AccountBalance {
  usd: number;
  oltin: number;
}

export interface Balances {
  total_usd: number;
  wallet: AccountBalance;
  exchange: AccountBalance;
  staking: AccountBalance;
}

export interface Transfer {
  id: string;
  direction: 'sent' | 'received';
  counterparty: string;
  amount: number;
  fee: number;
  status: 'pending' | 'confirmed' | 'failed';
  created_at: string;
}

export interface StakingInfo {
  balance: number;
  locked_until: string | null;
  is_locked: boolean;
  apy: number;
  daily_reward: number;
  total_earned: number;
}

export interface StakingReward {
  date: string;
  amount: number;
  balance_snapshot: number;
}

export interface Order {
  id: string;
  side: 'buy' | 'sell';
  order_type: 'limit' | 'market';
  price: number;
  quantity: number;
  filled_quantity: number;
  status: 'open' | 'filled' | 'cancelled';
  created_at: string;
}

export interface OrderbookLevel {
  price: number;
  quantity: number;
}

export interface Orderbook {
  bids: OrderbookLevel[];
  asks: OrderbookLevel[];
  mid_price: number;
}

export interface Trade {
  price: number;
  quantity: number;
  side: 'buy' | 'sell';
  created_at: string;
}

export interface FavoriteContact {
  id: string;
  oltin_id: string;
  created_at: string;
}

export interface RecentContact {
  oltin_id: string;
  last_transfer_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}
