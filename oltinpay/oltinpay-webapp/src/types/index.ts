// API Types

export interface User {
  id: string;
  telegram_id: number;
  oltin_id: string;
  language: 'uz' | 'ru';
  created_at: string;
}

// On-chain balances from GET /balances — all values are raw wei strings
// (uint256 doesn't fit a JS number). Format for display via lib/format.formatToken.
export interface WalletBalances {
  oltin_wei: string;
  uzd_wei: string;
}

export interface StakingBalances {
  total_principal_wei: string;
  unlocked_wei: string;
  pending_reward_wei: string;
  lot_count: number;
  next_unlock_at: number;
}

export interface BalancesResponse {
  wallet_address: string;
  wallet: WalletBalances;
  staking: StakingBalances;
}

// On-chain transaction feed from GET /transactions (indexer-backed). Mirrors the
// backend TransactionItem; amount_wei is a raw wei string, indexed_at is ISO.
export type TransactionDirection = 'in' | 'out' | 'self';

export interface Transaction {
  tx_hash: string;
  event_type: string;
  direction: TransactionDirection;
  block_number: number;
  from_address: string | null;
  to_address: string | null;
  amount_wei: string | null;
  explorer_url: string;
  indexed_at: string;
}

// GET /users/lookup?oltin_id= — resolve a recipient to their on-chain address.
// wallet_address is null when the recipient never onboarded a wallet.
export interface UserLookupResult {
  oltin_id: string;
  wallet_address: string | null;
}

// Exchange price + quote (por module, feed-derived — all UZS, not USD).
export interface FeedReading {
  answer: string;
  decimals: number;
  updated_at: number;
}

export interface RatesResponse {
  xau_usd: FeedReading;
  uzs_usd: FeedReading;
  oltin_price_uzd: number; // UZS per 1 OLTIN (1 gram of gold)
}

export type QuoteSide = 'buy' | 'sell';

// GET /quote?side=&amount= — estimate only (no minOut/fee); estimated_out_wei is
// an exact integer wei string (same floor formula as the on-chain swap).
export interface QuoteResponse {
  oltin_price_uzd: number;
  xau_answer: string;
  uzs_answer: string;
  xau_updated_at: number;
  uzs_updated_at: number;
  side: QuoteSide | null;
  amount: number | null;
  estimated_out: number | null;
  estimated_out_wei: string | null;
  estimated_out_symbol: string | null;
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
