"""
app/schemas/order.py
Pydantic v2 Data Transfer Objects (DTOs) for Orders and OrderItems.

Enforces schema contracts for:
- OrderItemInput: Client payload for selecting a product and quantity at checkout.
- OrderCreateRequest: Client payload containing a list of line items to purchase.
- OrderItemResponse: Public representation of an ordered line item with snapshotted
  pricing.
- OrderResponse: Public representation of an order with its current status and items.
- OrderStatusRequest: Admin payload to update an order's lifecycle status.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.order import OrderStatus


class OrderItemInput(BaseModel):
    """
    Client input representing a single line item when placing an order.
    Prices are never supplied by the client to prevent price tampering.
    """

    product_id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID v4) of the product to order",
    )
    quantity: int = Field(
        ...,
        ge=1,
        le=100,
        description="Quantity of this product to order (minimum 1, maximum 100)",
        examples=[2],
    )


class OrderCreateRequest(BaseModel):
    """
    Client request payload for placing a new food and coffee order.
    """

    items: list[OrderItemInput] = Field(
        ...,
        min_length=1,
        description="List of items to order. Must contain at least one item.",
    )

    @field_validator("items", mode="after")
    @classmethod
    def validate_unique_products(cls, v: list[OrderItemInput]) -> list[OrderItemInput]:
        """Prevent duplicate product_id entries in a single order request."""
        seen_ids: set[uuid.UUID] = set()
        for item in v:
            if item.product_id in seen_ids:
                raise ValueError(
                    f"Duplicate product_id {item.product_id} found in order. "
                    "Please combine quantities into a single item."
                )
            seen_ids.add(item.product_id)
        return v


class OrderItemResponse(BaseModel):
    """
    Public representation of a line item within an order.
    Snapshots the product name and unit price at the time of purchase.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID v4) of the order item",
    )
    product_id: uuid.UUID = Field(
        ...,
        description="Unique identifier of the ordered product",
    )
    product_name: str = Field(
        ...,
        description="Name of the product snapshotted at time of purchase",
        examples=["Cappuccino"],
    )
    quantity: int = Field(
        ...,
        ge=1,
        description="Quantity of the product purchased",
        examples=[2],
    )
    unit_price: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Unit price snapshotted at time of purchase",
        examples=[Decimal("3.00")],
    )
    subtotal: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Line-item total (quantity * unit_price)",
        examples=[Decimal("6.00")],
    )


class OrderResponse(BaseModel):
    """
    Public representation of an Order returned by API endpoints.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID v4) of the order",
    )
    user_id: uuid.UUID = Field(
        ...,
        description="UUID of the customer who placed the order",
    )
    status: OrderStatus = Field(
        ...,
        description="Current lifecycle status of the order",
        examples=[OrderStatus.PENDING],
    )
    total_amount: Decimal = Field(
        ...,
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Total order amount calculated server-side in USD",
        examples=[Decimal("15.50")],
    )
    items: list[OrderItemResponse] = Field(
        ...,
        description="List of individual items included in this order",
    )
    ordered_at: datetime = Field(
        ...,
        description="UTC timestamp when the order was placed",
    )


class OrderStatusRequest(BaseModel):
    """
    Request body for updating an order's lifecycle status (Admin only).
    """

    status: OrderStatus = Field(
        ...,
        description="New status to apply (CONFIRMED, COMPLETED, CANCELLED)",
        examples=[OrderStatus.CONFIRMED],
    )
