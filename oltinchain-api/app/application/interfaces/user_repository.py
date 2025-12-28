"""User repository interface."""

from typing import Protocol
from uuid import UUID

from app.infrastructure.models import User


class UserRepositoryProtocol(Protocol):
    """Protocol for user repository."""

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        ...

    async def get_by_phone(self, phone: str) -> User | None:
        """Get user by phone number."""
        ...

    async def create(self, phone: str, password_hash: str) -> User:
        """Create a new user."""
        ...

    async def update(self, user: User) -> User:
        """Update an existing user."""
        ...
