import { formatUnits, parseUnits } from 'viem';

const TOKEN_DECIMALS = 18;

/**
 * Format an 18-decimal token amount (a wei string from the on-chain `/balances`
 * response) for display with a thousands separator.
 *
 *   formatToken('1000000000000000000000000') -> '1,000,000'
 *   formatToken('1000000000000000000')       -> '1'
 *   formatToken('1500000000000000000')       -> '1.5'
 *   formatToken('0')                          -> '0'
 *
 * The integer part is grouped via BigInt (no Number precision loss for large
 * balances); the fraction is capped at `maxFractionDigits` and trailing zeros
 * are dropped.
 */
export function formatToken(wei: string, maxFractionDigits = 4): string {
  const decimal = formatUnits(BigInt(wei), TOKEN_DECIMALS); // '1000000' | '1.5' | '0'
  const [intPart, fracPart = ''] = decimal.split('.');
  const intFormatted = BigInt(intPart).toLocaleString('en-US'); // '1,000,000'
  const frac = fracPart.slice(0, maxFractionDigits).replace(/0+$/, '');
  return frac ? `${intFormatted}.${frac}` : intFormatted;
}

/**
 * Parse a user-entered token amount (a decimal string) to wei, or null when it
 * is empty, non-positive, or not a valid decimal. NEVER via parseFloat — an
 * 18-decimal amount does not survive a JS float round-trip, so the money path
 * parses the raw string straight to a bigint.
 *
 *   parseTokenAmount('1')    -> 1000000000000000000n
 *   parseTokenAmount('1.5')  -> 1500000000000000000n
 *   parseTokenAmount('')     -> null
 *   parseTokenAmount('0')    -> null
 *   parseTokenAmount('-1')   -> null
 *   parseTokenAmount('abc')  -> null
 */
export function parseTokenAmount(raw: string, decimals = TOKEN_DECIMALS): bigint | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    const wei = parseUnits(trimmed, decimals);
    return wei > BigInt(0) ? wei : null;
  } catch {
    return null;
  }
}

/**
 * Client-side slippage floor for an Exchange swap. The backend `/quote` returns
 * an exact-integer estimate (`estimated_out_wei`, same floor formula as the
 * on-chain swap) but no minOut — we floor it by the slippage tolerance
 * (default 1% = 100 bps). Returns null when the estimate is missing / non-positive
 * / not a number, OR the floored minOut would be 0 — the on-chain buy requires
 * `minOltinOut > 0`, and a 0 floor means the amount is too small to swap.
 */
export function computeMinOut(
  estimatedOutWei: string | null,
  slippageBps = 100,
): bigint | null {
  if (!estimatedOutWei) return null;
  let est: bigint;
  try {
    est = BigInt(estimatedOutWei);
  } catch {
    return null;
  }
  if (est <= BigInt(0)) return null;
  const minOut = (est * BigInt(10000 - slippageBps)) / BigInt(10000);
  return minOut > BigInt(0) ? minOut : null;
}
