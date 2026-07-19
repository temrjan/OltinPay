// Client-safe config (no secrets, no server env). Explorer deep links for the
// public dashboard's contract addresses and attestation transactions.
export const EXPLORER = "https://sepolia.explorer.zksync.io";

export const addressUrl = (address: string): string =>
  `${EXPLORER}/address/${address}`;

export const txUrl = (hash: string): string => `${EXPLORER}/tx/${hash}`;
