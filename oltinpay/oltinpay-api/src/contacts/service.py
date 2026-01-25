"""Contact service layer."""

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from src.contacts.models import FavoriteContact
from src.contacts.schemas import FavoriteContactResponse, RecentContactResponse
from src.transfers.models import Transfer
from src.users import service as user_service


async def get_recent_contacts(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 5,
) -> list[RecentContactResponse]:
    """Get recent transfer recipients.

    Returns last N unique recipients ordered by most recent transfer.
    """
    result = await db.execute(
        select(Transfer.to_user_id, Transfer.created_at)
        .where(Transfer.from_user_id == user_id)
        .order_by(Transfer.created_at.desc())
    )
    transfers = result.all()

    # Get unique recipients preserving order
    seen: set[UUID] = set()
    recent: list[tuple[UUID, Any]] = []
    for to_user_id, created_at in transfers:
        if to_user_id not in seen:
            seen.add(to_user_id)
            recent.append((to_user_id, created_at))
            if len(recent) >= limit:
                break

    # Fetch user details
    contacts: list[RecentContactResponse] = []
    for contact_user_id, last_transfer_at in recent:
        user = await user_service.get_user_by_id(db, contact_user_id)
        if user:
            contacts.append(
                RecentContactResponse(
                    oltin_id=f"@{user.oltin_id}",
                    last_transfer_at=last_transfer_at,
                )
            )

    return contacts


async def get_favorites(
    db: AsyncSession,
    user_id: UUID,
) -> list[FavoriteContactResponse]:
    """Get user's favorite contacts."""
    result = await db.execute(
        select(FavoriteContact)
        .where(FavoriteContact.user_id == user_id)
        .order_by(FavoriteContact.created_at.desc())
    )
    favorites = result.scalars().all()

    contacts: list[FavoriteContactResponse] = []
    for fav in favorites:
        user = await user_service.get_user_by_id(db, fav.contact_user_id)
        if user:
            contacts.append(
                FavoriteContactResponse(
                    id=fav.id,
                    oltin_id=f"@{user.oltin_id}",
                    created_at=fav.created_at,
                )
            )

    return contacts


async def add_favorite(
    db: AsyncSession,
    user_id: UUID,
    oltin_id: str,
) -> FavoriteContactResponse:
    """Add contact to favorites."""
    # Normalize oltin_id
    oltin_id_normalized = oltin_id.lower().strip()
    if oltin_id_normalized.startswith("@"):
        oltin_id_normalized = oltin_id_normalized[1:]

    # Find contact user
    contact_user = await user_service.get_user_by_oltin_id(db, oltin_id_normalized)
    if not contact_user:
        raise NotFoundException(f"User @{oltin_id_normalized} not found")

    # Cannot add self
    if contact_user.id == user_id:
        raise BadRequestException("Cannot add yourself to favorites")

    # Check if already favorited
    existing = await db.execute(
        select(FavoriteContact).where(
            FavoriteContact.user_id == user_id,
            FavoriteContact.contact_user_id == contact_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException("Contact already in favorites")

    # Create favorite with explicit UUID
    favorite_id = uuid.uuid4()
    now = datetime.now(UTC)

    favorite = FavoriteContact(
        id=favorite_id,
        user_id=user_id,
        contact_user_id=contact_user.id,
        created_at=now,
    )
    db.add(favorite)
    await db.flush()

    return FavoriteContactResponse(
        id=favorite_id,
        oltin_id=f"@{contact_user.oltin_id}",
        created_at=now,
    )


async def remove_favorite(
    db: AsyncSession,
    user_id: UUID,
    favorite_id: UUID,
) -> bool:
    """Remove contact from favorites."""
    result = await db.execute(
        select(FavoriteContact).where(
            FavoriteContact.id == favorite_id,
            FavoriteContact.user_id == user_id,
        )
    )
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise NotFoundException("Favorite contact not found")

    await db.delete(favorite)
    return True
