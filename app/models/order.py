"""
app/models/order.py
SQLAlchemy ORM models for Order and OrderItem entities with OrderStatus enum.

Implements:
- OrderStatus enum: PENDING, CONFIRMED, COMPLETED, CANCELLED.
- Order model: UUID PK, user_id (FK), status, total_amount, ordered_at.
- OrderItem model: UUID PK, order_id (FK), product_id (FK), quantity, unit_price.
- Relationships:
  - Order.user (joinedload)
  - Order.items (selectinload, cascade delete)
  - OrderItem.order
  - OrderItem.product (joinedload)
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.user import User


class OrderStatus(enum.StrEnum):
    """Lifecycle status of a food and coffee order."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Order(Base):
    """
    Order entity representing a purchase made by a user.

    Contains a snapshot of total_amount and a collection of OrderItems.
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
        index=True,
        nullable=False,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", native_enum=False),
        default=OrderStatus.PENDING,
        index=True,
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
    )
    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="orders",
        lazy="joined",
    )
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __init__(self, **kw: object) -> None:
        kw.setdefault("id", uuid.uuid4())
        kw.setdefault("status", OrderStatus.PENDING)
        kw.setdefault("total_amount", Decimal("0.00"))
        super().__init__(**kw)


class OrderItem(Base):
    """
    OrderItem entity representing an individual item within an Order.

    Snapshots the unit_price from the Product at the time the order was placed.
    """

    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="order_items",
        lazy="joined",
    )

    def __init__(self, **kw: object) -> None:
        kw.setdefault("id", uuid.uuid4())
        super().__init__(**kw)

    @property
    def subtotal(self) -> Decimal:
        """Calculate line-item total (quantity × snapshotted unit_price)."""
        return Decimal(self.quantity) * self.unit_price
