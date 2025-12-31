import { Wallet, Provider, ContractFactory } from "zksync-ethers";
import * as fs from "fs";
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
  console.log("Balance:", (Number(balance) / 1e18).toFixed(6), "ETH");
  
  const feeCollector = wallet.address;
  console.log("Fee Collector:", feeCollector);
  
  // Load zksync artifact
  const artifactPath = "./artifacts-zk/contracts/OltinTokenV2.sol/OltinTokenV2.json";
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  
  const factory = new ContractFactory(
    artifact.abi,
    artifact.bytecode,
    wallet
  );
  
  console.log("\nDeploying contract...");
  const contract = await factory.deploy(feeCollector);
  
  console.log("Waiting for confirmation...");
  await contract.waitForDeployment();
  
  const address = await contract.getAddress();
  
  console.log("\n=== SUCCESS ===");
  console.log("OltinTokenV2:", address);
  console.log("\nUpdate .env:");
  console.log("OLTIN_CONTRACT_ADDRESS_V2=" + address);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
