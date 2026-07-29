/**
 * Deployed contract addresses on zkSync Era Sepolia + minimal ABIs.
 */

import type {Address} from 'viem';

export const ZKSYNC_SEPOLIA_CHAIN_ID = 300;

export const CONTRACTS = {
  // Live V3/V3.1 addresses.
  OLTIN: '0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5' as Address,
  UZD: '0x51232fd0065bD2ca50551761Acef476E3CDf02aA' as Address,
  EXCHANGE: '0x99D733E64eb60c3B3D5f3DeDe4CC4adC92BCd1c9' as Address,
  STAKING: '0xD3b6ffd1dE409e1C37BA5B867d6eC3897A721fAa' as Address,
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

export const EXCHANGE_ABI = [
  {
    type: 'function',
    name: 'buy',
    stateMutability: 'nonpayable',
    inputs: [
      {name: 'uzdInWei', type: 'uint256'},
      {name: 'minOltinOut', type: 'uint256'},
    ],
    outputs: [{name: 'oltinOutWei', type: 'uint256'}],
  },
  {
    type: 'function',
    name: 'sell',
    stateMutability: 'nonpayable',
    inputs: [
      {name: 'oltinInWei', type: 'uint256'},
      {name: 'minUzdOut', type: 'uint256'},
    ],
    outputs: [{name: 'uzdOutWei', type: 'uint256'}],
  },
  {
    type: 'function',
    name: 'treasuryBalance',
    stateMutability: 'view',
    inputs: [],
    outputs: [{type: 'uint256'}],
  },
] as const;
