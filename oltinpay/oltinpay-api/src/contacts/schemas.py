"""Contact Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecentContactResponse(BaseModel):
    """Recent contact from transfers."""

    oltin_id: str
    last_transfer_at: datetime


class FavoriteContactResponse(BaseModel):
    """Favorite contact response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    oltin_id: str
    created_at: datetime


class FavoriteContactCreate(BaseModel):
    """Create favorite contact request."""

    oltin_id: str = Field(..., min_length=1, max_length=32)
