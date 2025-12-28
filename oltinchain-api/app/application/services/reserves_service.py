"""Reserves service for Proof of Reserves."""

from decimal import Decimal
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import GoldBar
from app.infrastructure.blockchain.zksync_client import ZkSyncClient
from app.domain.exceptions import BlockchainError

logger = structlog.get_logger()


class ReservesService:
    """Service for Proof of Reserves operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_proof_of_reserves(self) -> dict:
        """Calculate and return Proof of Reserves.
        
        Returns:
            Dict with total gold bars weight, on-chain supply, and coverage ratio
        """
        # Get total physical gold from database
        result = await self.session.execute(
            select(func.sum(GoldBar.weight_grams)).where(
                GoldBar.status == "active"
            )
        )
        total_physical_grams = result.scalar_one_or_none() or Decimal("0")

        # Get on-chain total supply
        try:
            client = ZkSyncClient()
            on_chain_supply = await client.get_total_supply()
            token_info = await client.get_token_info()
        except BlockchainError as e:
            logger.error("blockchain_error", error=str(e))
            on_chain_supply = Decimal("0")
            token_info = {"contract_address": "unavailable"}

        # Calculate coverage ratio
        if on_chain_supply > 0:
            coverage_ratio = total_physical_grams / on_chain_supply
        else:
            coverage_ratio = Decimal("1.0") if total_physical_grams > 0 else Decimal("0")

        # Determine status
        if coverage_ratio >= 1:
            status = "fully_backed"
        elif coverage_ratio >= Decimal("0.95"):
            status = "nearly_backed"
        else:
            status = "under_backed"

        # Count gold bars
        bar_count = await self.session.execute(
            select(func.count()).select_from(GoldBar).where(
                GoldBar.status == "active"
            )
        )
        total_bars = bar_count.scalar_one()

        return {
            "physical_gold": {
                "total_grams": str(total_physical_grams),
                "total_bars": total_bars,
            },
            "token_supply": {
                "total_supply": str(on_chain_supply),
                "contract_address": token_info.get("contract_address"),
            },
            "coverage": {
                "ratio": str(coverage_ratio),
                "percentage": str(coverage_ratio * 100),
                "status": status,
            },
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    async def lookup_gold_bar(self, serial_number: str) -> GoldBar | None:
        """Lookup a gold bar by serial number.
        
        Args:
            serial_number: Gold bar serial number
            
        Returns:
            GoldBar if found, None otherwise
        """
        result = await self.session.execute(
            select(GoldBar).where(GoldBar.serial_number == serial_number)
        )
        return result.scalar_one_or_none()

    async def get_all_gold_bars(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[GoldBar]:
        """Get list of all gold bars.
        
        Args:
            limit: Max items to return
            offset: Items to skip
            status: Filter by status (active, retired)
            
        Returns:
            List of GoldBar objects
        """
        query = select(GoldBar)

        if status:
            query = query.where(GoldBar.status == status)

        query = query.order_by(GoldBar.acquired_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())
