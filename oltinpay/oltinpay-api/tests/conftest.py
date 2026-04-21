"""Pytest configuration and fixtures."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import StaticPool, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.database import Base, get_db
from src.main import app

# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine with shared cache for in-memory SQLite
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Test session maker
test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Register custom function for SQLite to emulate gen_random_uuid()
@event.listens_for(test_engine.sync_engine, "connect")
def register_uuid_function(dbapi_conn, _connection_record):
    dbapi_conn.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Global session for test persistence
_test_session: AsyncSession | None = None


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override database dependency for tests - uses shared session."""
    global _test_session
    if _test_session is None:
        _test_session = test_session_maker()

    try:
        yield _test_session
        await _test_session.commit()
    except Exception:
        await _test_session.rollback()
        raise


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    global _test_session

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _test_session = test_session_maker()

    yield _test_session

    # Cleanup
    await _test_session.close()
    _test_session = None

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client wired to the in-memory test DB session."""
    _ = db_session  # Depend on the fixture so tables exist before requests hit.
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


def create_test_token(user_id: str | UUID) -> str:
    """Create JWT token for testing."""
    expire = datetime.now(UTC) + timedelta(minutes=30)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> dict[str, Any]:
    """Create test user in database."""
    from src.balances.models import AccountType, Balance, Currency
    from src.users.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        telegram_id=123456789,
        oltin_id="testuser",
        language="uz",
    )
    db_session.add(user)
    await db_session.flush()

    # Create balances for all account types
    for account_type in AccountType:
        for currency in Currency:
            # Skip staking USD (not allowed)
            if account_type == AccountType.STAKING and currency == Currency.USD:
                continue
            balance = Balance(
                id=uuid.uuid4(),
                user_id=user.id,
                account_type=account_type.value,
                currency=currency.value,
                amount=Decimal("100") if currency == Currency.USD else Decimal("10"),
            )
            db_session.add(balance)

    await db_session.commit()
    await db_session.refresh(user)

    token = create_test_token(user.id)

    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> dict[str, Any]:
    """Create second test user for transfer/contact tests."""
    from src.balances.models import AccountType, Balance, Currency
    from src.users.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        telegram_id=987654321,
        oltin_id="seconduser",
        language="ru",
    )
    db_session.add(user)
    await db_session.flush()

    # Create balances
    for account_type in AccountType:
        for currency in Currency:
            if account_type == AccountType.STAKING and currency == Currency.USD:
                continue
            balance = Balance(
                id=uuid.uuid4(),
                user_id=user.id,
                account_type=account_type.value,
                currency=currency.value,
                amount=Decimal("50") if currency == Currency.USD else Decimal("5"),
            )
            db_session.add(balance)

    await db_session.commit()
    await db_session.refresh(user)

    token = create_test_token(user.id)

    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }
