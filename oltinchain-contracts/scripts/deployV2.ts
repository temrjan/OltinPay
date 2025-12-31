import { Wallet, Provider } from "zksync-ethers";
import { HardhatRuntimeEnvironment } from "hardhat/types";
import { Deployer } from "@matterlabs/hardhat-zksync";
import * as dotenv from "dotenv";

dotenv.config();

export default async function (hre: HardhatRuntimeEnvironment) {
  console.log("=== Deploying OltinTokenV2 ===");
  
  const provider = new Provider("https://sepolia.era.zksync.dev");
  
  const wallet = new Wallet(
    process.env.MINTER_PRIVATE_KEY!,
    provider
  );
  
  console.log("Deployer:", wallet.address);
  console.log("Balance:", hre.ethers.formatEther(await provider.getBalance(wallet.address)), "ETH");
  
  const deployer = new Deployer(hre, wallet);
  
  // Fee collector = deployer (minter) address
  const feeCollector = wallet.address;
  
  console.log("Fee Collector:", feeCollector);
  
  const artifact = await deployer.loadArtifact("OltinTokenV2");
  
  const token = await deployer.deploy(artifact, [feeCollector]);
  
  const tokenAddress = await token.getAddress();
  
  console.log("\n=== Deployment Complete ===");
  console.log("OltinTokenV2:", tokenAddress);
  console.log("\nUpdate .env:");
  console.log(`OLTIN_CONTRACT_ADDRESS_V2=${tokenAddress}`);
  
  // Verify contract
  console.log("\nVerifying contract...");
  try {
    await hre.run("verify:verify", {
      address: tokenAddress,
      constructorArguments: [feeCollector],
    });
    console.log("Contract verified!");
  } catch (e) {
    console.log("Verification failed (may already be verified):", e);
  }
}
