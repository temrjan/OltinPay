// User types
export interface User {
  id: string
  phone: string
  wallet_address: string | null
}

// Balance types
export interface BalanceItem {
  available: number
  locked: number
  total: number
}

export interface Balance {
  usd: BalanceItem
  oltin: BalanceItem
  wallet_address: string | null
}

// Price types
export interface Price {
  price: number
  bid: number
  ask: number
  spread_percent: number
}

// Quote types
export interface BuyQuote {
  amount_usd: number
  amount_oltin: number
  price_per_gram: number
  fee_usd: number
  fee_percent: number
}

export interface SellQuote {
  amount_oltin: number
  amount_usd: number
  price_per_gram: number
  fee_usd: number
  fee_percent: number
}

// Transaction types
export type TransactionType =
  | 'buy'
  | 'sell'
  | 'transfer_in'
  | 'transfer_out'
  | 'deposit'
  | 'bonus'

export interface Transaction {
  id: string
  type: TransactionType
  amount_oltin?: string
  amount_usd?: string
  tx_hash?: string
  to_address?: string
  from_address?: string
  created_at: string
  status: 'pending' | 'completed' | 'failed'
}

// API Response types
export interface ApiError {
  detail: string
  code?: string
}

export interface TransferResponse {
  tx_hash: string
  status: string
}

// Navigation types
export interface NavItem {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  activeIcon?: React.ComponentType<{ className?: string }>
}
