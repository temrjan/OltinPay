import { describe, it, expect } from 'vitest';

import { computeMinOut, formatToken, parseTokenAmount } from './format';

describe('formatToken', () => {
  it('should group 1e24 wei (1,000,000 tokens) with a thousands separator', () => {
    // Reviewer nit: the test fixes the FINAL string, not the intermediate number.
    expect(formatToken('1000000000000000000000000')).toBe('1,000,000');
  });

  it('should format 1e18 wei as "1"', () => {
    expect(formatToken('1000000000000000000')).toBe('1');
  });

  it('should format 0 wei as "0"', () => {
    expect(formatToken('0')).toBe('0');
  });

  it('should keep a non-trivial fraction and drop trailing zeros', () => {
    expect(formatToken('1500000000000000000')).toBe('1.5');
  });

  it('should cap the fraction at maxFractionDigits (default 4)', () => {
    expect(formatToken('1234567890000000000')).toBe('1.2345');
  });

  it('should format a small sub-unit amount (0.001)', () => {
    expect(formatToken('1000000000000000')).toBe('0.001');
  });
});

describe('parseTokenAmount', () => {
  it('parses a whole number to wei', () => {
    expect(parseTokenAmount('1')).toBe(BigInt('1000000000000000000'));
  });

  it('parses a fractional amount to wei', () => {
    expect(parseTokenAmount('1.5')).toBe(BigInt('1500000000000000000'));
  });

  it('parses the smallest sub-unit (1 wei)', () => {
    expect(parseTokenAmount('0.000000000000000001')).toBe(BigInt(1));
  });

  it('rejects empty / whitespace as null', () => {
    expect(parseTokenAmount('')).toBeNull();
    expect(parseTokenAmount('   ')).toBeNull();
  });

  it('rejects zero as null', () => {
    expect(parseTokenAmount('0')).toBeNull();
  });

  it('rejects a negative amount as null', () => {
    expect(parseTokenAmount('-1')).toBeNull();
  });

  it('rejects non-numeric input as null', () => {
    expect(parseTokenAmount('abc')).toBeNull();
  });
});

describe('computeMinOut', () => {
  it('applies a 1% slippage floor (default)', () => {
    expect(computeMinOut('1000')).toBe(BigInt(990));
  });

  it('floors the integer division', () => {
    expect(computeMinOut('100')).toBe(BigInt(99)); // 100*9900/10000 = 99
  });

  it('handles a large wei value without precision loss', () => {
    expect(computeMinOut('1000000000000000000')).toBe(BigInt('990000000000000000'));
  });

  it('honors a custom slippage (2%)', () => {
    expect(computeMinOut('1000', 200)).toBe(BigInt(980));
  });

  it('returns null for null / empty estimate', () => {
    expect(computeMinOut(null)).toBeNull();
    expect(computeMinOut('')).toBeNull();
  });

  it('returns null for a zero / non-positive estimate', () => {
    expect(computeMinOut('0')).toBeNull();
  });

  it('returns null when the floored minOut is 0 (amount too small)', () => {
    expect(computeMinOut('1')).toBeNull(); // 1*9900/10000 = 0
  });

  it('returns null for a non-numeric estimate', () => {
    expect(computeMinOut('abc')).toBeNull();
  });
});
