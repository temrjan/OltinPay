"""API dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.domain.exceptions import AuthenticationError
from app.infrastructure.models import User
from app.infrastructure.repositories.user_repo import UserRepository
from app.infrastructure.security import decode_token


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> UUID:
    """Extract user_id from JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]

    try:
        payload = decode_token(token)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    return UUID(payload["sub"])


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Get current authenticated user."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    return user


# Type alias for convenience
CurrentUser = Annotated[User, Depends(get_current_user)]
