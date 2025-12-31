import { Wallet, Provider, Contract } from "zksync-ethers";
import * as fs from "fs";
import * as dotenv from "dotenv";

dotenv.config({ path: "../.env" });

const V1_ADDRESS = "0xA7E92168517864359B6Fa9e2247B01e0280A7dAa";
const V2_ADDRESS = "0x4A56B78DBFc2E6c914f5413B580e86ee1A474347";

const V2_ABI = [
  "function balanceOf(address) view returns (uint256)",
  "function mint(address to, uint256 amount, string orderId)",
  "function totalSupply() view returns (uint256)",
];

async function main() {
  console.log("=== Migration V1 -> V2 ===");
  
  const provider = new Provider("https://sepolia.era.zksync.dev");
  const wallet = new Wallet(process.env.MINTER_PRIVATE_KEY!, provider);
  
  console.log("Minter:", wallet.address);
  
  const balance = await provider.getBalance(wallet.address);
  console.log("ETH Balance:", (Number(balance) / 1e18).toFixed(4));
  
  // Read wallets
  const walletsRaw = fs.readFileSync("/tmp/wallets.txt", "utf8");
  const wallets = walletsRaw.split("\n").map(s => s.trim()).filter(Boolean);
  console.log("Total wallets:", wallets.length);
  
  const v1 = new Contract(V1_ADDRESS, ["function balanceOf(address) view returns (uint256)"], provider);
  const v2 = new Contract(V2_ADDRESS, V2_ABI, wallet);
  
  // Get all non-zero balances
  console.log("\nFetching V1 balances...");
  const toMigrate: { addr: string; balance: bigint }[] = [];
  
  for (let i = 0; i < wallets.length; i++) {
    const addr = wallets[i];
    try {
      const bal = await v1.balanceOf(addr);
      if (bal > 0n) {
        toMigrate.push({ addr, balance: bal });
        process.stdout.write(`\r  Found ${toMigrate.length} wallets with balance...`);
      }
    } catch (e) {
      // Skip invalid addresses
    }
  }
  
  console.log("\n\nWallets with balance:", toMigrate.length);
  
  const totalOltin = toMigrate.reduce((sum, w) => sum + w.balance, 0n);
  console.log("Total OLTIN to migrate:", (Number(totalOltin) / 1e18).toFixed(4));
  
  // Migrate
  console.log("\n--- Starting Migration ---");
  let success = 0;
  let failed = 0;
  
  for (let i = 0; i < toMigrate.length; i++) {
    const { addr, balance } = toMigrate[i];
    const grams = (Number(balance) / 1e18).toFixed(4);
    
    process.stdout.write(`[${i + 1}/${toMigrate.length}] ${addr.slice(0, 10)}... (${grams} OLTIN) `);
    
    try {
      const tx = await v2.mint(addr, balance, `mig-${addr.slice(2, 10)}`);
      await tx.wait();
      console.log("✓");
      success++;
    } catch (e: any) {
      console.log("✗", e.message?.slice(0, 50));
      failed++;
    }
  }
  
  console.log("\n=== Migration Complete ===");
  console.log("Success:", success);
  console.log("Failed:", failed);
  
  const v2Supply = await v2.totalSupply();
  console.log("V2 Total Supply:", (Number(v2Supply) / 1e18).toFixed(4), "OLTIN");
}

main().catch(console.error);
