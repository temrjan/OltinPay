import { Provider, Contract } from "zksync-ethers";
import * as dotenv from "dotenv";
dotenv.config({ path: "../.env" });

const V1_ADDRESS = "0xA7E92168517864359B6Fa9e2247B01e0280A7dAa";

const wallets = `
0x27d887d138813c6125e41f4eea23170537ca7978
0x986c0c9689281d454a97ca12db35f2ae2ea810d9
0xda558938057a14037e381b06de5ec8ef527d03bd
0xaf1f4402acbfd476d9366215c9cab6ab5e7de58f
0xd68abfc84e77342471eb10a3bf9c9b20d4745ef6
0x0533ad476876625e77c13de9e4bee85d67884615
0xd49b038af080a889e16e863f31ca432467be1862
0x49ec006e37fb8df66dc728223a6b6952582b1fbc
0x0dd795d948427d71b734418b2958ef8b9d28574c
0xe89983045baabd7d121ae373d81b0a2924a19c1c
0xaff2a7d832c279dac0cbf37ab79c1699524c0141
0x2e7e2115bcc09ccf45650725a4dadac1ab19ee41
0xc501be20ddec22f651181f4f439a18a013f7638a
0x1269f252a73a4242b4dee315b66e2066847afa31
0x992276848d5a32207425046b9fb1641e6f761a89
0x52dc7b1bc7ac719c877b2f98ab3cb5ca61377082
0x434f46494f97325f328e7d8dac198f1bffc5a8c1
0xd8f4db797173738ef3e736861fd1e6515056649b
0x4cc1a9cfaeb492dd7d3dbc664ed3fdaa66e16771
0x354335fbc534a93d462031a0dd7acf097094844c
0x736b2fa9a95e4e95b1491c2b0d25c971eb199b6a
0x0a0a9e87e4fdb0f1c92adec57aaf5f8ba936c2a2
0x1bf23178b8bd72cf200791c607affd94951d8e9e
0x6b42beea1fd3f8dc41a9ea054182529db4069b98
0xb8fe9f29704bb341765a2704633bd37e0f6af541
0x97635f990fcbe2f8428493f87685984288c95b36
0xebad9e8f5852ea3d3bfbcc01557f890949dd0e34
0xdB67883F0E1ec7353c67C83c1451A4f2d211627E
0xfd7d8ccb8a662975929142dd4886a654cf95bf64
0xcc303bdec28315ea14042110a3a965a92e0023ed
`.trim().split("\n").map(s => s.trim()).filter(Boolean);

async function main() {
  const provider = new Provider("https://sepolia.era.zksync.dev");
  const v1 = new Contract(V1_ADDRESS, ["function balanceOf(address) view returns (uint256)"], provider);
  
  const results: { addr: string; bal: string }[] = [];
  
  for (const addr of wallets.slice(0, 30)) {
    const balance = await v1.balanceOf(addr);
    if (balance > 0n) {
      results.push({ addr, bal: (Number(balance) / 1e18).toFixed(4) });
    }
  }
  
  console.log(JSON.stringify(results, null, 2));
}

main();
