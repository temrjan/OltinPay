import { Wallet, Provider, ContractFactory } from "zksync-ethers";
import * as hre from "hardhat";
import * as dotenv from "dotenv";

dotenv.config({ path: "../.env" });

async function main() {
  console.log("=== Deploying OltinTokenV2 ===");
  
  const provider = new Provider("https://sepolia.era.zksync.dev");
  
  const privateKey = process.env.MINTER_PRIVATE_KEY || process.env.PRIVATE_KEY;
  if (!privateKey) {
    throw new Error("No private key found");
  }
  
  const wallet = new Wallet(privateKey, provider);
  
  console.log("Deployer:", wallet.address);
  
  const balance = await provider.getBalance(wallet.address);
  console.log("Balance:", (Number(balance) / 1e18).toFixed(4), "ETH");
  
  // Fee collector = deployer
  const feeCollector = wallet.address;
  console.log("Fee Collector:", feeCollector);
  
  // Load artifact
  const artifact = await hre.artifacts.readArtifact("OltinTokenV2");
  
  const factory = new ContractFactory(
    artifact.abi,
    artifact.bytecode,
    wallet,
    "create"
  );
  
  console.log("Deploying...");
  const contract = await factory.deploy(feeCollector);
  await contract.waitForDeployment();
  
  const address = await contract.getAddress();
  console.log("\n=== Deployed ===");
  console.log("OltinTokenV2:", address);
  console.log("\nAdd to .env: OLTIN_CONTRACT_ADDRESS_V2=" + address);
}

main().catch(console.error);
