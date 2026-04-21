"""User service layer."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.balances.models import AccountType, Balance, Currency
from src.users.models import User
from src.users.schemas import OltinIdCreate, UserUpdate


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> User | None:
    """Get user by Telegram ID."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_user_by_oltin_id(db: AsyncSession, oltin_id: str) -> User | None:
    """Get user by oltin_id."""
    # Normalize oltin_id
    oltin_id = oltin_id.lower().strip()
    if oltin_id.startswith("@"):
        oltin_id = oltin_id[1:]

    result = await db.execute(select(User).where(User.oltin_id == oltin_id))
    return result.scalar_one_or_none()


async def check_oltin_id_available(db: AsyncSession, oltin_id: str) -> bool:
    """Check if oltin_id is available."""
    user = await get_user_by_oltin_id(db, oltin_id)
    return user is None


async def create_user(
    db: AsyncSession,
    telegram_id: int,
    oltin_id: str,
    language: str = "uz",
) -> User:
    """Create new user with initial balances.

    Creates user and 5 balance records:
    - wallet: USD (1000 demo), OLTIN (0)
    - exchange: USD (0), OLTIN (0)
    - staking: OLTIN (0)
    """
    # Create user
    user = User(
        telegram_id=telegram_id,
        oltin_id=oltin_id.lower(),
        language=language,
    )
    db.add(user)
    await db.flush()

    # Create initial balances
    initial_balances = [
        Balance(
            user_id=user.id,
            account_type=AccountType.WALLET,
            currency=Currency.USD,
            amount=Decimal("1000"),
        ),
        Balance(
            user_id=user.id,
            account_type=AccountType.WALLET,
            currency=Currency.OLTIN,
            amount=Decimal("0"),
        ),
        Balance(
            user_id=user.id,
            account_type=AccountType.EXCHANGE,
            currency=Currency.USD,
            amount=Decimal("0"),
        ),
        Balance(
            user_id=user.id,
            account_type=AccountType.EXCHANGE,
            currency=Currency.OLTIN,
            amount=Decimal("0"),
        ),
        Balance(
            user_id=user.id,
            account_type=AccountType.STAKING,
            currency=Currency.OLTIN,
            amount=Decimal("0"),
        ),
    ]

    for balance in initial_balances:
        db.add(balance)

    await db.flush()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    user: User,
    update_data: UserUpdate,
) -> User:
    """Update user data."""
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user


async def set_oltin_id(
    db: AsyncSession,
    user: User,
    data: OltinIdCreate,
) -> User:
    """Set oltin_id for user (only if not already set or placeholder)."""
    user.oltin_id = data.oltin_id.lower()
    await db.flush()
    await db.refresh(user)
    return user


async def get_user_by_wallet_address(
    db: AsyncSession, wallet_address: str
) -> User | None:
    """Get user by non-custodial wallet address (case-insensitive)."""
    normalized = wallet_address.lower()
    result = await db.execute(
        select(User).where(User.wallet_address == normalized)
    )
    return result.scalar_one_or_none()


async def set_wallet_address(
    db: AsyncSession, user: User, wallet_address: str
) -> User:
    """Attach a non-custodial wallet address to the user.

    Address is stored lowercase for lookup parity. Caller is responsible
    for rejecting attempts to overwrite an existing binding.
    """
    user.wallet_address = wallet_address.lower()
    await db.flush()
    await db.refresh(user)
    return user


async def search_users(
    db: AsyncSession,
    query: str,
    limit: int = 10,
) -> list[User]:
    """Search users by oltin_id prefix."""
    query = query.lower().strip()
    if query.startswith("@"):
        query = query[1:]

    result = await db.execute(
        select(User).where(User.oltin_id.ilike(f"{query}%")).limit(limit)
    )
    return list(result.scalars().all())
