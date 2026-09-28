"""
app/models/order.py
Order and OrderItem models with OrderStatus enum.

Implemented in: Task 2.4 (stub initialized for relationship resolution).
"""

import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase

if TYPE_CHECKING:
    from app.models.user import User


class Order(TimestampedBase):
    """
    Order entity representing food and coffee orders.
    Full schema (status, total_amount, items) will be implemented in Task 2.4.
    """

    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="orders")
