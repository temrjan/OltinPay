"""zkSync client with Paymaster support for gasless transfers."""

from decimal import Decimal
from typing import Optional

import structlog
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3
from web3.middleware import SignAndSendRawMiddlewareBuilder

from app.config import settings
from app.domain.exceptions import BlockchainError

logger = structlog.get_logger()

# Paymaster ABI (only needed functions)
PAYMASTER_ABI = [
    {
        "inputs": [{"name": "_to", "type": "address"}],
        "name": "withdrawFees",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalFeesCollected",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# ERC20 approval ABI
ERC20_APPROVE_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def get_paymaster_params(
    paymaster_address: str,
    token_address: str,
    min_allowance: int,
) -> dict:
    """
    Build paymasterParams for approval-based flow.
    
    zkSync SDK format for paymaster transactions.
    """
    # IPaymasterFlow.approvalBased selector
    selector = Web3.keccak(text="approvalBased(address,uint256,bytes)")[:4]
    
    # Encode parameters
    inner_input = b""  # No additional data
    encoded_params = Web3.solidity_keccak(
        ["address", "uint256", "bytes"],
        [token_address, min_allowance, inner_input]
    )
    
    paymaster_input = selector + Web3.to_bytes(hexstr=Web3.to_checksum_address(token_address))[12:] + \
                      min_allowance.to_bytes(32, "big") + \
                      (64).to_bytes(32, "big") + \
                      len(inner_input).to_bytes(32, "big") + \
                      inner_input
    
    return {
        "paymaster": Web3.to_checksum_address(paymaster_address),
        "paymasterInput": paymaster_input.hex(),
    }


class ZkSyncPaymasterClient:
    """zkSync client with Paymaster for gasless user transfers."""

    def __init__(self) -> None:
        self.w3 = Web3(Web3.HTTPProvider(settings.zksync_rpc_url))
        
        if not settings.minter_private_key:
            raise BlockchainError("MINTER_PRIVATE_KEY not configured")
        if not settings.oltin_contract_address:
            raise BlockchainError("OLTIN_CONTRACT_ADDRESS not configured")
        if not settings.paymaster_address:
            raise BlockchainError("PAYMASTER_ADDRESS not configured")

        self.minter_account = Account.from_key(settings.minter_private_key)
        self.w3.middleware_onion.inject(
            SignAndSendRawMiddlewareBuilder.build(self.minter_account),
            layer=0,
        )
        self.w3.eth.default_account = self.minter_account.address

        self.token_address = Web3.to_checksum_address(settings.oltin_contract_address)
        self.paymaster_address = Web3.to_checksum_address(settings.paymaster_address)

        logger.info(
            "zksync_paymaster_client_init",
            paymaster=self.paymaster_address,
            token=self.token_address,
        )

    def _to_wei(self, grams: Decimal) -> int:
        return int(grams * Decimal(10**18))

    def _from_wei(self, wei: int) -> Decimal:
        return Decimal(wei) / Decimal(10**18)

    async def transfer_with_paymaster(
        self,
        from_private_key: str,
        to_address: str,
        grams: Decimal,
    ) -> str:
        """
        Transfer OLTIN using Paymaster (gasless for user).
        
        User pays fee in OLTIN, Paymaster pays ETH gas.
        """
        try:
            amount_wei = self._to_wei(grams)
            to_checksum = Web3.to_checksum_address(to_address)
            
            sender_account = Account.from_key(from_private_key)
            sender_address = sender_account.address
            
            logger.info(
                "paymaster_transfer_start",
                from_addr=sender_address,
                to_addr=to_address,
                grams=str(grams),
            )
            
            # 1. Check/set allowance for Paymaster
            token_contract = self.w3.eth.contract(
                address=self.token_address,
                abi=ERC20_APPROVE_ABI + [{
                    "inputs": [
                        {"name": "to", "type": "address"},
                        {"name": "amount", "type": "uint256"},
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "stateMutability": "nonpayable",
                    "type": "function",
                }]
            )
            
            current_allowance = token_contract.functions.allowance(
                sender_address, self.paymaster_address
            ).call()
            
            # Fee estimate (0.5% of amount or minimum)
            estimated_fee = max(amount_wei * 50 // 10000, self._to_wei(Decimal("0.0001")))
            
            if current_allowance < estimated_fee:
                # Approve Paymaster to take fees
                approve_tx = token_contract.functions.approve(
                    self.paymaster_address,
                    2**256 - 1  # Max approval
                ).build_transaction({
                    "from": sender_address,
                    "nonce": self.w3.eth.get_transaction_count(sender_address),
                    "gas": 100000,
                    "gasPrice": self.w3.eth.gas_price,
                })
                
                # This approval still needs gas - use minter to sponsor
                # In production, do this once during user onboarding
                logger.info("approving_paymaster", user=sender_address)
            
            # 2. Build transfer with paymaster params
            paymaster_params = get_paymaster_params(
                self.paymaster_address,
                self.token_address,
                estimated_fee,
            )
            
            transfer_tx = token_contract.functions.transfer(
                to_checksum, amount_wei
            ).build_transaction({
                "from": sender_address,
                "nonce": self.w3.eth.get_transaction_count(sender_address),
                "gas": 150000,
                "maxFeePerGas": self.w3.eth.gas_price,
                "maxPriorityFeePerGas": self.w3.eth.gas_price,
                # zkSync specific
                "customData": {
                    "paymasterParams": paymaster_params,
                    "gasPerPubdata": 50000,
                },
            })
            
            # Sign and send
            signed_tx = sender_account.sign_transaction(transfer_tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info("paymaster_transfer_sent", tx_hash=tx_hash.hex())
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt["status"] != 1:
                raise BlockchainError(f"Transfer failed: {tx_hash.hex()}")
            
            logger.info(
                "paymaster_transfer_confirmed",
                tx_hash=tx_hash.hex(),
                gas_used=receipt["gasUsed"],
            )
            
            return tx_hash.hex()
            
        except Exception as e:
            logger.error("paymaster_transfer_failed", error=str(e))
            raise BlockchainError(f"Transfer failed: {e}") from e
