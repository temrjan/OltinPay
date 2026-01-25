"""Balance service layer."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.balances.models import AccountType, Balance, Currency
from src.balances.schemas import AccountBalance, BalancesResponse
from src.common.exceptions import BadRequestException, InsufficientBalanceException

# OLTIN price in USD (fixed for demo)
OLTIN_PRICE_USD = Decimal("100")


async def get_user_balances(db: AsyncSession, user_id: UUID) -> BalancesResponse:
    """Get all user balances."""
    result = await db.execute(select(Balance).where(Balance.user_id == user_id))
    balances = list(result.scalars().all())

    # Build response
    wallet_usd = Decimal("0")
    wallet_oltin = Decimal("0")
    exchange_usd = Decimal("0")
    exchange_oltin = Decimal("0")
    staking_oltin = Decimal("0")

    for b in balances:
        if b.account == AccountType.WALLET:
            if b.currency == Currency.USD:
                wallet_usd = b.amount
            else:
                wallet_oltin = b.amount
        elif b.account == AccountType.EXCHANGE:
            if b.currency == Currency.USD:
                exchange_usd = b.amount
            else:
                exchange_oltin = b.amount
        elif b.account == AccountType.STAKING:
            staking_oltin = b.amount

    # Calculate total in USD
    total_usd = (
        wallet_usd
        + exchange_usd
        + (wallet_oltin + exchange_oltin + staking_oltin) * OLTIN_PRICE_USD
    )

    return BalancesResponse(
        total_usd=total_usd,
        wallet=AccountBalance(usd=wallet_usd, oltin=wallet_oltin),
        exchange=AccountBalance(usd=exchange_usd, oltin=exchange_oltin),
        staking=AccountBalance(usd=Decimal("0"), oltin=staking_oltin),
    )


async def get_balance(
    db: AsyncSession,
    user_id: UUID,
    account: str,
    currency: str,
) -> Balance | None:
    """Get specific balance."""
    result = await db.execute(
        select(Balance).where(
            Balance.user_id == user_id,
            Balance.account == account,
            Balance.currency == currency,
        )
    )
    return result.scalar_one_or_none()


async def internal_transfer(
    db: AsyncSession,
    user_id: UUID,
    from_account: str,
    to_account: str,
    currency: str,
    amount: Decimal,
) -> None:
    """Transfer between user's own accounts.

    Rules:
    - Staking only supports OLTIN
    - Free (no fee)
    """
    # Validate staking constraints
    is_staking_involved = (
        from_account == AccountType.STAKING or to_account == AccountType.STAKING
    )
    if is_staking_involved and currency != Currency.OLTIN:
        raise BadRequestException("Staking account only supports OLTIN")

    # Get source balance
    from_balance = await get_balance(db, user_id, from_account, currency)
    if not from_balance or from_balance.amount < amount:
        raise InsufficientBalanceException(f"Insufficient {currency} in {from_account}")

    # Get destination balance
    to_balance = await get_balance(db, user_id, to_account, currency)
    if not to_balance:
        raise BadRequestException(f"Invalid destination account: {to_account}")

    # Perform transfer
    from_balance.amount -= amount
    to_balance.amount += amount

    await db.flush()
