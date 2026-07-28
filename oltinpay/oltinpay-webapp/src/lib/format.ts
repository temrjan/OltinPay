import { formatUnits } from 'viem';

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
