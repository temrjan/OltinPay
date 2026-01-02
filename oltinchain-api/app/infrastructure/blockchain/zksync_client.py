"""zkSync blockchain client for OltinToken V2 operations."""

from decimal import Decimal

import structlog
from eth_account import Account
from web3 import Web3
from web3.middleware import SignAndSendRawMiddlewareBuilder

from app.config import settings
from app.domain.exceptions import BlockchainError

logger = structlog.get_logger()

# OltinTokenV2 ABI
OLTIN_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "orderId", "type": "string"},
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "orderId", "type": "string"},
        ],
        "name": "burn",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "transferId", "type": "string"},
        ],
        "name": "adminTransfer",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "transferFeeBps",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "feeCollector",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class ZkSyncClient:
    """Client for interacting with OltinTokenV2 on zkSync."""

    def __init__(self) -> None:
        """Initialize the zkSync client."""
        self.w3 = Web3(Web3.HTTPProvider(settings.zksync_rpc_url))

        if not settings.minter_private_key:
            raise BlockchainError("MINTER_PRIVATE_KEY not configured")

        if not settings.oltin_contract_address:
            raise BlockchainError("OLTIN_CONTRACT_ADDRESS not configured")

        # Setup minter account
        self.minter_account = Account.from_key(settings.minter_private_key.get_secret_value())

        # Add signing middleware for minter
        self.w3.middleware_onion.inject(
            SignAndSendRawMiddlewareBuilder.build(self.minter_account),
            layer=0,
        )
        self.w3.eth.default_account = self.minter_account.address

        # Setup contract
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(settings.oltin_contract_address),
            abi=OLTIN_ABI,
        )

        logger.info(
            "zksync_client_initialized",
            rpc_url=settings.zksync_rpc_url,
            contract=settings.oltin_contract_address,
            minter=self.minter_account.address,
        )

    def _to_wei(self, grams: Decimal) -> int:
        """Convert grams to wei (18 decimals)."""
        return int(grams * Decimal(10**18))

    def _from_wei(self, wei: int) -> Decimal:
        """Convert wei to grams."""
        return Decimal(wei) / Decimal(10**18)

    async def mint(self, to_address: str, grams: Decimal, order_id: str) -> str:
        """Mint OLTIN tokens."""
        try:
            amount_wei = self._to_wei(grams)
            to_checksum = Web3.to_checksum_address(to_address)

            logger.info(
                "mint_starting",
                to=to_address,
                grams=str(grams),
                wei=amount_wei,
                order_id=order_id,
            )

            tx_hash = self.contract.functions.mint(to_checksum, amount_wei, order_id).transact()

            logger.info("mint_tx_sent", tx_hash=tx_hash.hex())

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] != 1:
                raise BlockchainError(f"Mint transaction failed: {tx_hash.hex()}")

            logger.info(
                "mint_confirmed",
                tx_hash=tx_hash.hex(),
                block=receipt["blockNumber"],
                gas_used=receipt["gasUsed"],
            )

            return tx_hash.hex()

        except Exception as e:
            logger.error("mint_failed", error=str(e), order_id=order_id)
            raise BlockchainError(f"Mint failed: {e}") from e

    async def burn(self, from_address: str, grams: Decimal, order_id: str) -> str:
        """Burn OLTIN tokens."""
        try:
            amount_wei = self._to_wei(grams)
            from_checksum = Web3.to_checksum_address(from_address)

            logger.info(
                "burn_starting",
                from_addr=from_address,
                grams=str(grams),
                wei=amount_wei,
                order_id=order_id,
            )

            tx_hash = self.contract.functions.burn(from_checksum, amount_wei, order_id).transact()

            logger.info("burn_tx_sent", tx_hash=tx_hash.hex())

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] != 1:
                raise BlockchainError(f"Burn transaction failed: {tx_hash.hex()}")

            logger.info(
                "burn_confirmed",
                tx_hash=tx_hash.hex(),
                block=receipt["blockNumber"],
                gas_used=receipt["gasUsed"],
            )

            return tx_hash.hex()

        except Exception as e:
            logger.error("burn_failed", error=str(e), order_id=order_id)
            raise BlockchainError(f"Burn failed: {e}") from e

    async def admin_transfer(
        self,
        from_address: str,
        to_address: str,
        grams: Decimal,
        transfer_id: str,
    ) -> tuple[str, Decimal, Decimal]:
        """
        Transfer OLTIN using adminTransfer (gasless for users).

        Args:
            from_address: Sender wallet address
            to_address: Recipient wallet address
            grams: Amount in grams (total, fee will be deducted)
            transfer_id: Unique transfer ID

        Returns:
            Tuple of (tx_hash, net_amount, fee_amount)
        """
        try:
            amount_wei = self._to_wei(grams)
            from_checksum = Web3.to_checksum_address(from_address)
            to_checksum = Web3.to_checksum_address(to_address)

            # Get fee percentage from contract
            fee_bps = self.contract.functions.transferFeeBps().call()
            fee_wei = (amount_wei * fee_bps) // 10000
            net_wei = amount_wei - fee_wei

            logger.info(
                "admin_transfer_starting",
                from_addr=from_address,
                to_addr=to_address,
                grams=str(grams),
                fee_bps=fee_bps,
                transfer_id=transfer_id,
            )

            tx_hash = self.contract.functions.adminTransfer(
                from_checksum, to_checksum, amount_wei, transfer_id
            ).transact()

            logger.info("admin_transfer_tx_sent", tx_hash=tx_hash.hex())

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] != 1:
                raise BlockchainError(f"Transfer failed: {tx_hash.hex()}")

            net_grams = self._from_wei(net_wei)
            fee_grams = self._from_wei(fee_wei)

            logger.info(
                "admin_transfer_confirmed",
                tx_hash=tx_hash.hex(),
                block=receipt["blockNumber"],
                gas_used=receipt["gasUsed"],
                net_grams=str(net_grams),
                fee_grams=str(fee_grams),
            )

            return tx_hash.hex(), net_grams, fee_grams

        except Exception as e:
            logger.error("admin_transfer_failed", error=str(e), transfer_id=transfer_id)
            raise BlockchainError(f"Transfer failed: {e}") from e

    async def get_balance(self, address: str) -> Decimal:
        """Get OLTIN balance for an address."""
        checksum = Web3.to_checksum_address(address)
        wei = self.contract.functions.balanceOf(checksum).call()
        return self._from_wei(wei)

    async def get_total_supply(self) -> Decimal:
        """Get total OLTIN supply."""
        wei = self.contract.functions.totalSupply().call()
        return self._from_wei(wei)

    async def get_transfer_fee_bps(self) -> int:
        """Get transfer fee in basis points."""
        return self.contract.functions.transferFeeBps().call()

    async def get_token_info(self) -> dict:
        """Get token metadata."""
        return {
            "name": self.contract.functions.name().call(),
            "symbol": self.contract.functions.symbol().call(),
            "decimals": self.contract.functions.decimals().call(),
            "total_supply": str(await self.get_total_supply()),
            "transfer_fee_bps": await self.get_transfer_fee_bps(),
            "contract_address": settings.oltin_contract_address,
        }
