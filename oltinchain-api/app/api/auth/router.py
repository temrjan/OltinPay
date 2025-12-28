"""Auth API router."""

from fastapi import APIRouter, Depends, HTTPException
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


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    """Get auth service dependency."""
    user_repo = UserRepository(session)
    return AuthService(user_repo)


@router.post("/register", response_model=TokenResponse)
async def register(
    data: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user."""
    try:
        result = await auth_service.register(data.phone, data.password)
        return TokenResponse(**result)
    except UserAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Phone already registered")


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate a user."""
    try:
        result = await auth_service.login(data.phone, data.password)
        return TokenResponse(**result)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token."""
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        result = await auth_service.refresh_tokens(payload["sub"])
        return TokenResponse(**result)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
