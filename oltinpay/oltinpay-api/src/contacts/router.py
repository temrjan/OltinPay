"""Contacts router."""

from uuid import UUID

from fastapi import APIRouter, status

from src.auth.dependencies import CurrentUser, DbSession
from src.contacts import service
from src.contacts.schemas import (
    FavoriteContactCreate,
    FavoriteContactResponse,
    RecentContactResponse,
)

router = APIRouter()


@router.get("/recent", response_model=list[RecentContactResponse])
async def get_recent_contacts(
    current_user: CurrentUser,
    db: DbSession,
) -> list[RecentContactResponse]:
    """Get last 5 transfer recipients."""
    return await service.get_recent_contacts(db, current_user.id, limit=5)


@router.get("/favorites", response_model=list[FavoriteContactResponse])
async def get_favorites(
    current_user: CurrentUser,
    db: DbSession,
) -> list[FavoriteContactResponse]:
    """Get favorite contacts."""
    return await service.get_favorites(db, current_user.id)


@router.post(
    "/favorites",
    response_model=FavoriteContactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite(
    request: FavoriteContactCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> FavoriteContactResponse:
    """Add contact to favorites."""
    return await service.add_favorite(db, current_user.id, request.oltin_id)


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    favorite_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Remove contact from favorites."""
    await service.remove_favorite(db, current_user.id, favorite_id)
