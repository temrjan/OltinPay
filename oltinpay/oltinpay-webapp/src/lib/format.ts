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
