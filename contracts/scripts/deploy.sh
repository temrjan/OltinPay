#!/usr/bin/env bash
# Interactive deploy wrapper for UZD + OltinStaking on zkSync Sepolia.
#
# - Prompts for PRIVATE_KEY without echoing to screen or shell history.
# - Injects it only into the hardhat subprocess environment.
# - Does NOT persist the key to any file.
#
# Usage: ./scripts/deploy.sh

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v npx &> /dev/null; then
  echo "ERROR: npx not found. Install Node.js first."
  exit 1
fi

if [[ ! -d node_modules ]]; then
  echo "Installing deps..."
  npm install
fi

echo ""
echo "=== Deploy UZD + OltinStaking to zkSync Sepolia ==="
echo "Signer must have Sepolia zkSync ETH for gas."
echo ""
read -s -p "PRIVATE_KEY (64 hex chars, will not be shown): " PRIVATE_KEY
echo ""

if [[ -z "${PRIVATE_KEY:-}" ]]; then
  echo "ERROR: empty key"
  exit 1
fi

# Strip optional 0x prefix — hardhat-zksync accepts both
PRIVATE_KEY="${PRIVATE_KEY#0x}"

# Validate length
if [[ ${#PRIVATE_KEY} -ne 64 ]]; then
  echo "ERROR: private key must be 64 hex chars (found ${#PRIVATE_KEY})"
  unset PRIVATE_KEY
  exit 1
fi

echo ""
echo "Compiling for zkSync..."
PRIVATE_KEY="$PRIVATE_KEY" npx hardhat compile --network zkSyncSepolia

echo ""
echo "Deploying..."
PRIVATE_KEY="$PRIVATE_KEY" npx hardhat deploy-zksync \
  --network zkSyncSepolia \
  --script deploy-uzd-staking.ts

# Clear the variable after use
unset PRIVATE_KEY

echo ""
echo "✓ Done. Copy the UZD and OltinStaking addresses from above and paste"
echo "  them into the chat or docs/PROGRESS.md."
