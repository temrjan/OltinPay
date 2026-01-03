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
        """Get user by phone number."""
        result = await self.session.execute(select(User).where(User.phone == phone))
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
