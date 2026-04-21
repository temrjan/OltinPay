/**
 * Deployed contract addresses on zkSync Era Sepolia + minimal ABIs.
 */

import type {Address} from 'viem';

export const ZKSYNC_SEPOLIA_CHAIN_ID = 300;

export const CONTRACTS = {
  OLTIN: '0x4A56B78DBFc2E6c914f5413B580e86ee1A474347' as Address,
  UZD: '0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32' as Address,
  STAKING: '0x63e537A3a150d06035151E29904C1640181C8314' as Address,
} as const;

// Minimal ABIs — only what the frontend actually calls.
export const ERC20_ABI = [
  {
    type: 'function',
    name: 'balanceOf',
    stateMutability: 'view',
    inputs: [{name: 'account', type: 'address'}],
    outputs: [{type: 'uint256'}],
  },
  {
    type: 'function',
    name: 'decimals',
    stateMutability: 'view',
    inputs: [],
    outputs: [{type: 'uint8'}],
  },
  {
    type: 'function',
    name: 'symbol',
    stateMutability: 'view',
    inputs: [],
    outputs: [{type: 'string'}],
  },
  {
    type: 'function',
    name: 'transfer',
    stateMutability: 'nonpayable',
    inputs: [
      {name: 'to', type: 'address'},
      {name: 'value', type: 'uint256'},
    ],
    outputs: [{type: 'bool'}],
  },
  {
    type: 'function',
    name: 'approve',
    stateMutability: 'nonpayable',
    inputs: [
      {name: 'spender', type: 'address'},
      {name: 'value', type: 'uint256'},
    ],
    outputs: [{type: 'bool'}],
  },
  {
    type: 'event',
    name: 'Transfer',
    inputs: [
      {name: 'from', type: 'address', indexed: true},
      {name: 'to', type: 'address', indexed: true},
      {name: 'value', type: 'uint256', indexed: false},
    ],
  },
] as const;

export const STAKING_ABI = [
  {
    type: 'function',
    name: 'stake',
    stateMutability: 'nonpayable',
    inputs: [{name: 'amount', type: 'uint256'}],
    outputs: [],
  },
  {
    type: 'function',
    name: 'unstake',
    stateMutability: 'nonpayable',
    inputs: [{name: 'amount', type: 'uint256'}],
    outputs: [],
  },
  {
    type: 'function',
    name: 'claim',
    stateMutability: 'nonpayable',
    inputs: [],
    outputs: [{name: 'paid', type: 'uint256'}],
  },
  {
    type: 'function',
    name: 'compound',
    stateMutability: 'nonpayable',
    inputs: [],
    outputs: [{name: 'added', type: 'uint256'}],
  },
  {
    type: 'function',
    name: 'pendingReward',
    stateMutability: 'view',
    inputs: [{name: 'user', type: 'address'}],
    outputs: [{type: 'uint256'}],
  },
  {
    type: 'function',
    name: 'getStakeInfo',
    stateMutability: 'view',
    inputs: [{name: 'user', type: 'address'}],
    outputs: [
      {name: 'totalPrincipal', type: 'uint256'},
      {name: 'unlocked', type: 'uint256'},
      {name: 'pending', type: 'uint256'},
      {name: 'lotCount', type: 'uint256'},
      {name: 'nextUnlockAt', type: 'uint256'},
    ],
  },
  {
    type: 'function',
    name: 'unlockedPrincipal',
    stateMutability: 'view',
    inputs: [{name: 'user', type: 'address'}],
    outputs: [{type: 'uint256'}],
  },
] as const;
