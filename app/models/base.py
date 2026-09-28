"""
app/models/base.py
Base and TimestampedBase declarative models for SQLAlchemy 2.0.

Provides:
- Base: Declarative root for all SQLAlchemy ORM models.
- TimestampedBase: Abstract base class with created_at and updated_at (UTC).
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Root declarative base class for all SQLAlchemy 2.0 ORM models in Cocoloco API.
    Alembic migrations use Base.metadata to discover all database tables.
    """

    def __repr__(self) -> str:
        """Informative __repr__ that safely prints only loaded attributes."""
        attrs = [
            f"{key}={value!r}"
            for key, value in self.__dict__.items()
            if not key.startswith("_")
        ]
        return f"{self.__class__.__name__}({', '.join(attrs)})"


class TimestampedBase(Base):
    """
    Abstract declarative base class adding audit timestamp columns.

    - created_at: Timestamp when record is inserted (UTC, server_default=now()).
    - updated_at: Timestamp when record is updated (UTC, server_default=now(),
      onupdate=now()).
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
