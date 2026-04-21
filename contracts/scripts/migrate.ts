import { Wallet, Provider, Contract } from "zksync-ethers";
import * as fs from "fs";
import * as dotenv from "dotenv";

dotenv.config({ path: "../.env" });

const V1_ADDRESS = "0xA7E92168517864359B6Fa9e2247B01e0280A7dAa";
const V2_ADDRESS = "0x4A56B78DBFc2E6c914f5413B580e86ee1A474347";

// User wallets (from DB)
const WALLETS = [
  "0x27d887d138813c6125e41f4eea23170537ca7978",
  "0x986c0c9689281d454a97ca12db35f2ae2ea810d9",
  "0xda558938057a14037e381b06de5ec8ef527d03bd",
  // Add more addresses here...
];

const ERC20_ABI = [
  "function balanceOf(address) view returns (uint256)",
  "function mint(address to, uint256 amount, string orderId)",
];

async function main() {
  console.log("=== Migration V1 -> V2 ===");
  
  const provider = new Provider("https://sepolia.era.zksync.dev");
  const wallet = new Wallet(process.env.MINTER_PRIVATE_KEY!, provider);
  
  console.log("Minter:", wallet.address);
  
  const v1 = new Contract(V1_ADDRESS, ERC20_ABI, provider);
  const v2 = new Contract(V2_ADDRESS, ERC20_ABI, wallet);
  
  // Get all balances first
  console.log("\nFetching balances from V1...");
  const toMigrate: { address: string; balance: bigint }[] = [];
  
  for (const addr of WALLETS) {
    const balance = await v1.balanceOf(addr);
    if (balance > 0n) {
      toMigrate.push({ address: addr, balance });
      console.log(`  ${addr}: ${Number(balance) / 1e18} OLTIN`);
    }
  }
  
  console.log(`\nTotal to migrate: ${toMigrate.length} wallets`);
  
  // Mint on V2
  console.log("\nMinting on V2...");
  for (let i = 0; i < toMigrate.length; i++) {
    const { address, balance } = toMigrate[i];
    console.log(`[${i + 1}/${toMigrate.length}] Minting to ${address}...`);
    
    try {
      const tx = await v2.mint(address, balance, `migration-v1-${address.slice(0, 8)}`);
      await tx.wait();
      console.log(`  ✓ Done: ${tx.hash}`);
    } catch (e: any) {
      console.error(`  ✗ Failed: ${e.message}`);
    }
  }
  
  console.log("\n=== Migration Complete ===");
}

main().catch(console.error);
