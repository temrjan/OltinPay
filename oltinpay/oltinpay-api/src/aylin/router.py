"""Aylin AI router."""

from fastapi import APIRouter

from src.auth.dependencies import CurrentUser
from src.aylin import service
from src.aylin.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: CurrentUser,
) -> ChatResponse:
    """Chat with Aylin AI assistant."""
    return await service.chat(
        message=request.message,
        user_language=current_user.language,
    )
