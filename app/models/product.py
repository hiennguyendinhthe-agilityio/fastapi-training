"""
app/models/product.py
SQLAlchemy ORM model for Product entity and CategoryType enum.

Implements:
- CategoryType enum: coffee, pastry, bundle, seasonal.
- Product model: UUID PK, name, description, price (Numeric 10,2),
  image_url, category, is_available.
"""

import enum
import uuid
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Enum, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class CategoryType(enum.StrEnum):
    """Product catalog categories matching Flutter menu tabs."""

    COFFEE = "coffee"
    PASTRY = "pastry"
    BUNDLE = "bundle"
    SEASONAL = "seasonal"


class Product(TimestampedBase):
    """Product entity representing food, coffee, bundles, and seasonal items."""

    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
    )
    image_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        default=None,
    )
    category: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, name="category_type", native_enum=False),
        index=True,
        nullable=False,
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    def __init__(self, **kw: object) -> None:
        kw.setdefault("id", uuid.uuid4())
        kw.setdefault("is_available", True)
        super().__init__(**kw)
