// Public PoR / rates response shapes — snake_case, mirroring the API's
// src/por/schemas.py (which is snake_case "like the user API"). Keep in sync.

export interface PorContractAddresses {
  oltin: string;
  uzd: string;
  reserve_attestor: string;
  exchange: string;
}

export interface PorResponse {
  reserve_answer: string;
  reserve_decimals: number;
  reserve_grams: number;
  reserve_updated_at: number; // unix seconds; 0 = never posted
  oltin_total_supply_wei: string;
  oltin_decimals: number;
  oltin_supply: number;
  // 1 OLTIN == 1 gram, coverage = reserve_grams / oltin_supply. >= 1 == fully
  // backed. null when nothing is in circulation (supply == 0).
  coverage_ratio: number | null;
  contracts: PorContractAddresses;
}

export interface FeedReading {
  answer: string;
  decimals: number;
  updated_at: number;
}

export interface RatesResponse {
  xau_usd: FeedReading;
  uzs_usd: FeedReading;
  oltin_price_uzd: number;
}

export interface PorHistoryItem {
  answer: string;
  block_number: number;
  tx_hash: string;
  indexed_at: string; // ISO 8601
}
