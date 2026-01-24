"""User repository implementation."""

from decimal import Decimal
from uuid import UUID

import structlog
from cryptography.fernet import Fernet
from eth_account import Account
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.models import Balance, User

logger = structlog.get_logger()

# Welcome bonus for new users (demo mode)
WELCOME_BONUS_USD = Decimal("1000")  # 1000 USD welcome bonus


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption."""
    # Use SECRET_KEY as encryption key (derive 32-byte key)
    import base64
    import hashlib

    key = hashlib.sha256(settings.secret_key.get_secret_value().encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def generate_wallet() -> tuple[str, str]:
    """Generate new Ethereum wallet.

    Returns:
        Tuple of (address, encrypted_private_key)
    """
    # Generate random account
    account = Account.create()
    address = account.address
    private_key = account.key.hex()

    # Encrypt private key
    fernet = get_fernet()
    encrypted = fernet.encrypt(private_key.encode()).decode()

    return address, encrypted


def decrypt_private_key(encrypted: str) -> str:
    """Decrypt user's private key."""
    fernet = get_fernet()
    return fernet.decrypt(encrypted.encode()).decode()


class UserRepository:
    """SQLAlchemy implementation of user repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> User | None:
        """Get user by phone number.

        Searches for phone in multiple formats to handle legacy data
        where some phones have '+' prefix and some don't.
        """
        # Normalize phone - remove +, spaces, dashes
        normalized = phone.replace("+", "").replace(" ", "").replace("-", "")
        # Search for both formats: with and without +
        phone_variants = [normalized, f"+{normalized}"]
        result = await self.session.execute(select(User).where(User.phone.in_(phone_variants)))
        return result.scalar_one_or_none()

    async def get_by_wallet_address(self, address: str) -> User | None:
        """Get user by wallet address."""
        result = await self.session.execute(select(User).where(User.wallet_address == address))
        return result.scalar_one_or_none()

    async def create(self, phone: str, password_hash: str) -> User:
        """Create a new user with wallet and welcome bonus."""
        # Generate wallet
        wallet_address, encrypted_private_key = generate_wallet()

        # Create user
        user = User(
            phone=phone,
            password_hash=password_hash,
            wallet_address=wallet_address,
            encrypted_private_key=encrypted_private_key,
        )
        self.session.add(user)
        await self.session.flush()  # Get user.id

        # Create USD balance with welcome bonus
        usd_balance = Balance(
            user_id=user.id,
            asset="USD",
            available=WELCOME_BONUS_USD,
            locked=Decimal("0"),
        )
        self.session.add(usd_balance)

        # Create OLTIN balance (empty)
        oltin_balance = Balance(
            user_id=user.id,
            asset="OLTIN",
            available=Decimal("0"),
            locked=Decimal("0"),
        )
        self.session.add(oltin_balance)

        await self.session.commit()
        await self.session.refresh(user)

        logger.info(
            "user_created_with_wallet",
            user_id=str(user.id),
            phone=phone,
            wallet_address=wallet_address,
            welcome_bonus_usd=str(WELCOME_BONUS_USD),
        )

        return user

    async def update(self, user: User) -> User:
        """Update an existing user."""
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def create_from_telegram(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        photo_url: str | None,
    ) -> User:
        """Create a new user from Telegram Mini App auth."""
        # Generate wallet
        wallet_address, encrypted_private_key = generate_wallet()

        # Create user with Telegram data
        user = User(
            phone=f"tg_{telegram_id}",  # Placeholder for required field
            password_hash="telegram_auth",  # Not used for Telegram auth
            wallet_address=wallet_address,
            encrypted_private_key=encrypted_private_key,
            telegram_id=telegram_id,
            telegram_username=username,
            telegram_first_name=first_name,
            telegram_photo_url=photo_url,
        )
        self.session.add(user)
        await self.session.flush()

        # Create USD balance with welcome bonus
        usd_balance = Balance(
            user_id=user.id,
            asset="USD",
            available=WELCOME_BONUS_USD,
            locked=Decimal("0"),
        )
        self.session.add(usd_balance)

        # Create OLTIN balance (empty)
        oltin_balance = Balance(
            user_id=user.id,
            asset="OLTIN",
            available=Decimal("0"),
            locked=Decimal("0"),
        )
        self.session.add(oltin_balance)

        await self.session.commit()
        await self.session.refresh(user)

        logger.info(
            "user_created_from_telegram",
            user_id=str(user.id),
            telegram_id=telegram_id,
            telegram_username=username,
            wallet_address=wallet_address,
        )

        return user

    async def update_telegram_data(
        self,
        user: User,
        username: str | None,
        first_name: str | None,
        photo_url: str | None,
    ) -> User:
        """Update user Telegram data if changed."""
        changed = False
        if user.telegram_username != username:
            user.telegram_username = username
            changed = True
        if user.telegram_first_name != first_name:
            user.telegram_first_name = first_name
            changed = True
        if user.telegram_photo_url != photo_url:
            user.telegram_photo_url = photo_url
            changed = True

        if changed:
            await self.session.commit()
            await self.session.refresh(user)
            logger.info("user_telegram_data_updated", user_id=str(user.id))

        return user
