"""Domain layer: SQLAlchemy ORM models — User, Product, Order, OrderItem."""

from app.models.base import Base, TimestampedBase

__all__ = [
    "Base",
    "TimestampedBase",
]
