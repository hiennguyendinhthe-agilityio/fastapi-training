"""
app/models/user.py
SQLAlchemy ORM model for User entity and UserRole enum.

Implements:
- UserRole enum: ADMIN, USER.
- User model: UUID primary key, clerk_id UK, email UK, full_name, role, is_active.
- Relationship: orders (1-to-Many).
"""

import enum
import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase

if TYPE_CHECKING:
    from app.models.order import Order


class UserRole(enum.StrEnum):
    """User authorization roles."""

    ADMIN = "ADMIN"
    USER = "USER"

    @property
    def is_admin(self) -> bool:
        """Check if role is ADMIN."""
        return self == UserRole.ADMIN


class User(TimestampedBase):
    """
    User entity representing customers and administrators.

    Authentication is managed externally by Clerk (RS256 JWKS).
    The clerk_id field serves as the subject identifier (sub) from Clerk JWTs.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    clerk_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __init__(self, **kw: object) -> None:
        kw.setdefault("id", uuid.uuid4())
        kw.setdefault("role", UserRole.USER)
        kw.setdefault("is_active", True)
        super().__init__(**kw)

    @property
    def is_admin(self) -> bool:
        """Helper to quickly check if user has ADMIN privileges."""
        return self.role == UserRole.ADMIN
