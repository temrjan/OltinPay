"""Contact database models."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class FavoriteContact(Base):
    """User's favorite contact."""

    __tablename__ = "favorite_contacts"

    __table_args__ = (
        UniqueConstraint("user_id", "contact_user_id", name="uq_favorite_contact"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    contact_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[contact_user_id],
    )

    def __repr__(self) -> str:
        return f"<FavoriteContact(id={self.id}, user_id={self.user_id})>"


from src.users.models import User  # noqa: E402, TC001
