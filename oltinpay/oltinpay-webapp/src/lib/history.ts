import { zeroAddress } from 'viem';

import type { Transaction } from '@/types';

// A transaction prepared for the history list: the correct token symbol + a
// display kind, with mint/burn double-records collapsed.
export type HistoryKind = 'received' | 'sent' | 'minted' | 'burned' | 'self';

export interface DisplayTx {
  tx_hash: string;
  symbol: 'UZD' | 'OLTIN';
  kind: HistoryKind;
  amount_wei: string | null;
  explorer_url: string;
  indexed_at: string;
}

// Token symbol from the event_type prefix. null for non-token events
// (reserve_answer) — those never reach a user feed but are skipped defensively.
function symbolOf(eventType: string): 'UZD' | 'OLTIN' | null {
  if (eventType.startsWith('uzd_')) return 'UZD';
  if (eventType.startsWith('oltin_')) return 'OLTIN';
  return null;
}

const isZero = (addr: string | null): boolean =>
  (addr ?? '').toLowerCase() === zeroAddress;

function kindOf(tx: Transaction): HistoryKind {
  const isTransfer = tx.event_type.endsWith('_transfer');
  // A mint is a *_minted event OR a transfer FROM the zero address; a burn is a
  // *_admin_burned event OR a transfer TO the zero address (OLTIN has no BURNER
  // role, so its burn only ever surfaces as a transfer to 0x0).
  if (tx.event_type.endsWith('_minted') || (isTransfer && isZero(tx.from_address))) {
    return 'minted';
  }
  if (tx.event_type.endsWith('_admin_burned') || (isTransfer && isZero(tx.to_address))) {
    return 'burned';
  }
  if (tx.direction === 'self') return 'self';
  return tx.direction === 'in' ? 'received' : 'sent';
}

/**
 * Prepare the on-chain transaction feed for display.
 *
 * - Skips non-token events (reserve_answer).
 * - Collapses the mint/burn double-record: a mint emits a `*_minted` event AND
 *   a `Transfer` from the zero address (same tx + token + amount); an admin burn
 *   emits `*_admin_burned` AND a `Transfer` to the zero address. Keep the
 *   minted/burned event, drop the paired zero-address transfer. A LONE
 *   zero-address transfer with no minted/burned event (an OLTIN sell/burn) is
 *   kept — dropping it would erase that leg.
 * - Attaches the correct token symbol + a display kind.
 */
export function prepareHistory(txs: Transaction[]): DisplayTx[] {
  const tokenTxs = txs.filter((tx) => symbolOf(tx.event_type) !== null);

  // Keys (tx_hash|symbol|amount) that have a minted/burned event — their paired
  // zero-address transfer is redundant. Match by tx+token+amount, NOT address
  // (a *_minted row has from_address=null, its paired transfer has from=0x0).
  const collapsed = new Set<string>();
  for (const tx of tokenTxs) {
    if (tx.event_type.endsWith('_minted') || tx.event_type.endsWith('_admin_burned')) {
      collapsed.add(`${tx.tx_hash}|${symbolOf(tx.event_type)}|${tx.amount_wei}`);
    }
  }

  const deduped = tokenTxs.filter((tx) => {
    if (!tx.event_type.endsWith('_transfer')) return true;
    if (!isZero(tx.from_address) && !isZero(tx.to_address)) return true; // normal transfer
    return !collapsed.has(`${tx.tx_hash}|${symbolOf(tx.event_type)}|${tx.amount_wei}`);
  });

  return deduped.map((tx) => ({
    tx_hash: tx.tx_hash,
    symbol: symbolOf(tx.event_type) as 'UZD' | 'OLTIN',
    kind: kindOf(tx),
    amount_wei: tx.amount_wei,
    explorer_url: tx.explorer_url,
    indexed_at: tx.indexed_at,
  }));
}
