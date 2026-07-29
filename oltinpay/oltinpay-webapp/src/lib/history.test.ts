import { describe, it, expect } from 'vitest';

import { prepareHistory } from './history';
import type { Transaction } from '@/types';

const ZERO = '0x0000000000000000000000000000000000000000';
const USER = '0x4a75707d25679d7002d4467785360595eb7b8882';
const OTHER = '0xf30b1acaa5365aa710f20aaeb0e2e8ccbbfcb35c';

function mk(over: Partial<Transaction>): Transaction {
  return {
    tx_hash: '0xtx',
    event_type: 'oltin_transfer',
    direction: 'out',
    block_number: 1,
    from_address: USER,
    to_address: OTHER,
    amount_wei: '1000000000000000000',
    explorer_url: 'https://explorer/0xtx',
    indexed_at: '2026-07-29T00:00:00Z',
    ...over,
  };
}

describe('prepareHistory', () => {
  it('collapses a UZD mint (minted + transfer-from-0x0) into one minted row', () => {
    const out = prepareHistory([
      mk({ tx_hash: '0xa', event_type: 'uzd_minted', direction: 'in', from_address: null, to_address: USER, amount_wei: '1000000000000000000000000' }),
      mk({ tx_hash: '0xa', event_type: 'uzd_transfer', direction: 'in', from_address: ZERO, to_address: USER, amount_wei: '1000000000000000000000000' }),
    ]);
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({ symbol: 'UZD', kind: 'minted', amount_wei: '1000000000000000000000000' });
  });

  it('collapses a UZD admin burn (burned + transfer-to-0x0) into one burned row', () => {
    const out = prepareHistory([
      mk({ tx_hash: '0xb', event_type: 'uzd_admin_burned', direction: 'out', from_address: USER, to_address: null }),
      mk({ tx_hash: '0xb', event_type: 'uzd_transfer', direction: 'out', from_address: USER, to_address: ZERO }),
    ]);
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({ symbol: 'UZD', kind: 'burned' });
  });

  it('keeps a lone OLTIN burn (transfer-to-0x0, no BURNED event) — the sell leg', () => {
    const out = prepareHistory([
      mk({ tx_hash: '0xc', event_type: 'oltin_transfer', direction: 'out', from_address: USER, to_address: ZERO, amount_wei: '100000000000000000' }),
    ]);
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({ symbol: 'OLTIN', kind: 'burned', amount_wei: '100000000000000000' });
  });

  it('splits a BUY into two honest legs (minted OLTIN + sent UZD), dropping the 0x0 transfer', () => {
    const out = prepareHistory([
      mk({ tx_hash: '0xd', event_type: 'oltin_minted', direction: 'in', from_address: null, to_address: USER, amount_wei: '634502341779686' }),
      mk({ tx_hash: '0xd', event_type: 'oltin_transfer', direction: 'in', from_address: ZERO, to_address: USER, amount_wei: '634502341779686' }),
      mk({ tx_hash: '0xd', event_type: 'uzd_transfer', direction: 'out', from_address: USER, to_address: OTHER, amount_wei: '100000000000000000000000' }),
    ]);
    expect(out).toHaveLength(2);
    expect(out.map((t) => `${t.symbol}:${t.kind}`).sort()).toEqual(['OLTIN:minted', 'UZD:sent']);
  });

  it('labels a normal outgoing OLTIN transfer as sent and incoming as received', () => {
    const [sent] = prepareHistory([mk({ event_type: 'oltin_transfer', direction: 'out', from_address: USER, to_address: OTHER })]);
    expect(sent).toMatchObject({ symbol: 'OLTIN', kind: 'sent' });
    const [recv] = prepareHistory([mk({ event_type: 'oltin_transfer', direction: 'in', from_address: OTHER, to_address: USER })]);
    expect(recv).toMatchObject({ kind: 'received' });
  });

  it('marks a self-transfer as self (not sent)', () => {
    const [row] = prepareHistory([mk({ event_type: 'oltin_transfer', direction: 'self', from_address: USER, to_address: USER })]);
    expect(row.kind).toBe('self');
  });

  it('skips reserve_answer (non-token event never pollutes the feed)', () => {
    const out = prepareHistory([
      mk({ event_type: 'reserve_answer', from_address: null, to_address: null, amount_wei: null }),
      mk({ event_type: 'oltin_transfer', direction: 'in', from_address: OTHER, to_address: USER }),
    ]);
    expect(out).toHaveLength(1);
    expect(out[0].symbol).toBe('OLTIN');
  });

  it('derives the symbol from the event_type prefix', () => {
    const [uzd] = prepareHistory([mk({ event_type: 'uzd_transfer', direction: 'in', from_address: OTHER, to_address: USER })]);
    expect(uzd.symbol).toBe('UZD');
  });
});
