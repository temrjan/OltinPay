import { Wallet, Provider } from "zksync-ethers";
import { Deployer } from "@matterlabs/hardhat-zksync";
import * as hre from "hardhat";
import * as dotenv from "dotenv";

dotenv.config();

async function main() {
  console.log("Deploying OltinToken to zkSync...");

  // Initialize provider and wallet
  const provider = new Provider(hre.network.config.url as string);
  
  if (!process.env.PRIVATE_KEY) {
    throw new Error("PRIVATE_KEY not set in .env");
  }
  
  const wallet = new Wallet(process.env.PRIVATE_KEY, provider);
  console.log("Deployer address:", wallet.address);

  // Check balance
  const balance = await provider.getBalance(wallet.address);
  console.log("Deployer balance:", balance.toString(), "wei");

  if (balance === 0n) {
    throw new Error("Deployer has no ETH for gas. Get testnet ETH from faucet.");
  }

  // Deploy
  const deployer = new Deployer(hre, wallet);
  const artifact = await deployer.loadArtifact("OltinToken");
  
  console.log("Deploying contract...");
  const contract = await deployer.deploy(artifact);
  await contract.waitForDeployment();

  const contractAddress = await contract.getAddress();
  console.log("\n✅ OltinToken deployed to:", contractAddress);
  console.log("\nVerify with:");
  console.log(`npx hardhat verify --network zkSyncSepolia ${contractAddress}`);

  // Verify roles
  const MINTER_ROLE = await contract.MINTER_ROLE();
  const hasMinterRole = await contract.hasRole(MINTER_ROLE, wallet.address);
  console.log("\nDeployer has MINTER_ROLE:", hasMinterRole);

  return contractAddress;
}

main()
  .then((address) => {
    console.log("\nDeployment successful!");
    process.exit(0);
  })
  .catch((error) => {
    console.error("Deployment failed:", error);
    process.exit(1);
  });
