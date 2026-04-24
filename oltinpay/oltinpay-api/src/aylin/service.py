"""AI assistant service layer."""

from uuid import UUID

import httpx

from src.aylin.schemas import ChatResponse, ChatSource
from src.config import settings


async def chat(message: str, user_id: UUID, user_language: str = "uz") -> ChatResponse:
    """Send message to znai-cloud RAG API and get response.

    Args:
        message: User's question
        user_id: User ID for session tracking
        user_language: User's preferred language (uz/ru/en)

    Returns:
        ChatResponse with AI response and sources
    """
    # Check if znai-cloud is configured
    if not settings.znai_cloud_url or not settings.znai_cloud_api_key:
        return ChatResponse(
            response="AI assistant is not configured. Please set ZNAI_CLOUD_URL and ZNAI_CLOUD_API_KEY.",
            sources=[],
        )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.znai_cloud_url}/public/chat",
                headers={
                    "X-API-Key": settings.znai_cloud_api_key.get_secret_value(),
                    "Content-Type": "application/json",
                },
                json={
                    "message": message,
                    "language": user_language,
                    "session_id": str(user_id),
                },
            )
            response.raise_for_status()
            data = response.json()

            sources = [
                ChatSource(
                    title=src.get("title", "Source"),
                    url=src.get("url"),
                )
                for src in data.get("sources", [])
            ]

            return ChatResponse(
                response=data.get("response", ""),
                sources=sources,
            )

    except httpx.HTTPStatusError as e:
        return ChatResponse(
            response=f"Error communicating with AI assistant: {e.response.status_code}",
            sources=[],
        )
    except httpx.RequestError:
        return ChatResponse(
            response="AI assistant is temporarily unavailable. Please try again later.",
            sources=[],
        )
