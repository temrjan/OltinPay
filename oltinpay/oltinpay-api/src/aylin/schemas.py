"""Aylin AI Pydantic schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request to Aylin AI."""

    message: str = Field(..., min_length=1, max_length=1000)


class ChatSource(BaseModel):
    """Source document reference."""

    title: str
    url: str | None = None


class ChatResponse(BaseModel):
    """Chat response from Aylin AI."""

    response: str
    sources: list[ChatSource] = []
