import { Wallet, Provider } from "zksync-ethers";
import { HardhatRuntimeEnvironment } from "hardhat/types";
import { Deployer } from "@matterlabs/hardhat-zksync";
import * as dotenv from "dotenv";

dotenv.config();

export default async function (hre: HardhatRuntimeEnvironment) {
  const provider = new Provider("https://sepolia.era.zksync.dev");
  
  const wallet = new Wallet(
    process.env.DEPLOYER_PRIVATE_KEY!,
    provider
  );
  
  const deployer = new Deployer(hre, wallet);
  
  // OLTIN token address (already deployed)
  const OLTIN_TOKEN = process.env.OLTIN_CONTRACT_ADDRESS!;
  
  console.log("Deploying OltinPaymaster...");
  console.log("OLTIN Token:", OLTIN_TOKEN);
  console.log("Deployer:", wallet.address);
  
  const artifact = await deployer.loadArtifact("OltinPaymaster");
  
  const paymaster = await deployer.deploy(artifact, [OLTIN_TOKEN]);
  
  const paymasterAddress = await paymaster.getAddress();
  console.log("OltinPaymaster deployed to:", paymasterAddress);
  
  // Fund paymaster with ETH for gas
  console.log("Funding paymaster with ETH...");
  const fundTx = await wallet.sendTransaction({
    to: paymasterAddress,
    value: hre.ethers.parseEther("0.01"), // 0.01 ETH for gas
  });
  await fundTx.wait();
  console.log("Funded with 0.01 ETH");
  
  console.log("\n=== Deployment Complete ===");
  console.log("Paymaster:", paymasterAddress);
  console.log("\nAdd to .env:");
  console.log(`PAYMASTER_ADDRESS=${paymasterAddress}`);
}
