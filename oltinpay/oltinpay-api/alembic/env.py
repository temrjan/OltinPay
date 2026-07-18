# mypy: ignore-errors
"""Alembic migration environment."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import all models so they register on Base.metadata. NOTE: src.exchange and
# src.staking have NO models module on disk — importing them broke every alembic
# command (ModuleNotFoundError). They are intentionally absent here.
from src.balances.models import Balance  # noqa: F401
from src.bank.models import BankDeposit, ReserveAttestation  # noqa: F401
from src.config import settings
from src.contacts.models import FavoriteContact  # noqa: F401
from src.database import Base
from src.indexer.models import ChainEvent  # noqa: F401
from src.transfers.models import Transfer  # noqa: F401
from src.users.models import User  # noqa: F401
from src.welcome.models import WelcomeClaim  # noqa: F401
from src.withdrawals.models import Withdrawal  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from settings."""
    return str(settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
