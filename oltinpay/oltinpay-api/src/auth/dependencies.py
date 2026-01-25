"""Auth dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import TokenPayload
from src.common.exceptions import UnauthorizedException
from src.config import settings
from src.database import get_db
from src.users import service as user_service
from src.users.models import User

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
        token_data = TokenPayload(**payload)

        if token_data.type != "access":
            raise UnauthorizedException("Invalid token type")

    except JWTError:
        raise UnauthorizedException("Could not validate credentials") from None

    user = await user_service.get_user_by_id(db, UUID(token_data.sub))

    if not user:
        raise UnauthorizedException("User not found")

    return user


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
