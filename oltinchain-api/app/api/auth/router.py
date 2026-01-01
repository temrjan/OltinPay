"""Auth API router with rate limiting."""

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.application.services.auth_service import AuthService
from app.database import get_session
from app.domain.exceptions import AuthenticationError, UserAlreadyExistsError
from app.infrastructure.repositories.user_repo import UserRepository
from app.infrastructure.security import decode_token

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiter - uses Redis in production
limiter = Limiter(key_func=get_remote_address)


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    """Get auth service dependency."""
    user_repo = UserRepository(session)
    return AuthService(user_repo)


@router.post("/register", response_model=TokenResponse)
@limiter.limit("3/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user. Rate limited to 3 requests per minute."""
    try:
        result = await auth_service.register(data.phone, data.password)
        return TokenResponse(**result)
    except UserAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Phone already registered")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate a user. Rate limited to 5 requests per minute."""
    try:
        result = await auth_service.login(data.phone, data.password)
        return TokenResponse(**result)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    data: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token. Rate limited to 10 requests per minute."""
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        result = await auth_service.refresh_tokens(payload["sub"])
        return TokenResponse(**result)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
