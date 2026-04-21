/**
 * viem clients for zkSync Era Sepolia.
 *
 * Read operations use a public client. Writes are signed locally with
 * an HD account derived from the user's BIP39 seed (kept in memory
 * during the unlocked session).
 */

import {createPublicClient, createWalletClient, http} from 'viem';
import {zksyncSepoliaTestnet} from 'viem/chains';
import type {Address, Hex} from 'viem';
import type {HDAccount} from 'viem/accounts';

import {CONTRACTS, ERC20_ABI, STAKING_ABI} from './contracts';

export const publicClient = createPublicClient({
  chain: zksyncSepoliaTestnet,
  transport: http(),
});

export function makeWalletClient(account: HDAccount) {
  return createWalletClient({
    account,
    chain: zksyncSepoliaTestnet,
    transport: http(),
  });
}

// ═══════════════════════════════════════════════════════════════════
// Reads
// ═══════════════════════════════════════════════════════════════════

export async function getOltinBalance(address: Address): Promise<bigint> {
  return publicClient.readContract({
    address: CONTRACTS.OLTIN,
    abi: ERC20_ABI,
    functionName: 'balanceOf',
    args: [address],
  });
}

export async function getUzdBalance(address: Address): Promise<bigint> {
  return publicClient.readContract({
    address: CONTRACTS.UZD,
    abi: ERC20_ABI,
    functionName: 'balanceOf',
    args: [address],
  });
}

export interface StakeInfo {
  totalPrincipal: bigint;
  unlocked: bigint;
  pending: bigint;
  lotCount: bigint;
  nextUnlockAt: bigint;
}

export async function getStakeInfo(address: Address): Promise<StakeInfo> {
  const [totalPrincipal, unlocked, pending, lotCount, nextUnlockAt] =
    await publicClient.readContract({
      address: CONTRACTS.STAKING,
      abi: STAKING_ABI,
      functionName: 'getStakeInfo',
      args: [address],
    });
  return {totalPrincipal, unlocked, pending, lotCount, nextUnlockAt};
}

// ═══════════════════════════════════════════════════════════════════
// Writes (require unlocked HD account)
// ═══════════════════════════════════════════════════════════════════

export async function transferOltin(
  account: HDAccount,
  to: Address,
  amount: bigint,
): Promise<Hex> {
  const wallet = makeWalletClient(account);
  return wallet.writeContract({
    address: CONTRACTS.OLTIN,
    abi: ERC20_ABI,
    functionName: 'transfer',
    args: [to, amount],
  });
}

export async function approveStakingForOltin(
  account: HDAccount,
  amount: bigint,
): Promise<Hex> {
  const wallet = makeWalletClient(account);
  return wallet.writeContract({
    address: CONTRACTS.OLTIN,
    abi: ERC20_ABI,
    functionName: 'approve',
    args: [CONTRACTS.STAKING, amount],
  });
}

export async function stake(account: HDAccount, amount: bigint): Promise<Hex> {
  const wallet = makeWalletClient(account);
  return wallet.writeContract({
    address: CONTRACTS.STAKING,
    abi: STAKING_ABI,
    functionName: 'stake',
    args: [amount],
  });
}

export async function unstake(account: HDAccount, amount: bigint): Promise<Hex> {
  const wallet = makeWalletClient(account);
  return wallet.writeContract({
    address: CONTRACTS.STAKING,
    abi: STAKING_ABI,
    functionName: 'unstake',
    args: [amount],
  });
}

export async function claimStakingReward(account: HDAccount): Promise<Hex> {
  const wallet = makeWalletClient(account);
  return wallet.writeContract({
    address: CONTRACTS.STAKING,
    abi: STAKING_ABI,
    functionName: 'claim',
  });
}
