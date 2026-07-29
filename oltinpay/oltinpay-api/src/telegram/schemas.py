"""Minimal Telegram Update models — only the fields the webhook reads.

Telegram sends large, evolving Update objects; ``extra="ignore"`` keeps parsing
tolerant of everything we don't use, so an added field never breaks the webhook.
"""

from pydantic import BaseModel, ConfigDict, Field


class TgChat(BaseModel):
    """Chat an incoming message belongs to."""

    id: int


class TgUser(BaseModel):
    """Sender of an incoming message (only the language hint is used)."""

    language_code: str | None = None


class TgMessage(BaseModel):
    """Incoming message — text plus who/where it came from."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    chat: TgChat
    text: str | None = None
    # ``from`` is a Python keyword, so it is exposed as ``from_user``.
    from_user: TgUser | None = Field(default=None, alias="from")


class TgUpdate(BaseModel):
    """A single webhook update. Only ``message`` is handled."""

    model_config = ConfigDict(extra="ignore")

    message: TgMessage | None = None
