"""Auth router."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import AuthResponse, TelegramAuthRequest
from src.auth.utils import create_access_token, validate_telegram_init_data
from src.common.exceptions import UnauthorizedException
from src.database import get_db
from src.users import service as user_service
from src.users.schemas import UserResponse

router = APIRouter()


@router.post("/telegram", response_model=AuthResponse)
async def authenticate_telegram(
    request: TelegramAuthRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Authenticate user via Telegram initData.

    If user doesn't exist, creates new user with temporary oltin_id.
    """
    # Validate Telegram initData
    telegram_user = validate_telegram_init_data(request.init_data)
    if not telegram_user:
        raise UnauthorizedException("Invalid Telegram authentication data")

    # Check if user exists
    user = await user_service.get_user_by_telegram_id(db, telegram_user.id)
    is_new = False

    if not user:
        # Create new user
        # Use telegram username if available, otherwise generate temp id
        oltin_id = telegram_user.username or f"user_{telegram_user.id}"

        # Check if oltin_id is taken
        if not await user_service.check_oltin_id_available(db, oltin_id):
            oltin_id = f"user_{telegram_user.id}"

        # Determine language
        language = "ru" if telegram_user.language_code == "ru" else "uz"

        user = await user_service.create_user(
            db,
            telegram_id=telegram_user.id,
            oltin_id=oltin_id,
            language=language,
        )
        is_new = True

    # Create access token
    access_token = create_access_token(str(user.id))

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
        is_new=is_new,
    )
