"""
tests/test_order_schemas.py
Comprehensive unit tests for Order Pydantic v2 schemas:
- OrderItemInput
- OrderCreateRequest
- OrderItemResponse
- OrderResponse
- OrderStatusRequest
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import CategoryType, Product
from app.schemas.order import (
    OrderCreateRequest,
    OrderItemInput,
    OrderItemResponse,
    OrderResponse,
    OrderStatusRequest,
)


class TestOrderItemInput:
    """Tests for OrderItemInput schema."""

    def test_order_item_input_valid(self) -> None:
        """Test valid OrderItemInput creation."""
        pid = uuid.uuid4()
        item = OrderItemInput(product_id=pid, quantity=3)
        assert item.product_id == pid
        assert item.quantity == 3

    def test_order_item_input_boundary_quantities(self) -> None:
        """Test valid boundary quantities 1 and 100."""
        pid = uuid.uuid4()
        item_min = OrderItemInput(product_id=pid, quantity=1)
        assert item_min.quantity == 1

        item_max = OrderItemInput(product_id=pid, quantity=100)
        assert item_max.quantity == 100

    def test_order_item_input_zero_quantity_fails(self) -> None:
        """Test that quantity < 1 raises ValidationError."""
        with pytest.raises(ValidationError):
            OrderItemInput(product_id=uuid.uuid4(), quantity=0)

    def test_order_item_input_negative_quantity_fails(self) -> None:
        """Test that negative quantity raises ValidationError."""
        with pytest.raises(ValidationError):
            OrderItemInput(product_id=uuid.uuid4(), quantity=-2)

    def test_order_item_input_excessive_quantity_fails(self) -> None:
        """Test that quantity > 100 raises ValidationError."""
        with pytest.raises(ValidationError):
            OrderItemInput(product_id=uuid.uuid4(), quantity=101)

    def test_order_item_input_invalid_uuid_fails(self) -> None:
        """Test that non-UUID string raises ValidationError."""
        with pytest.raises(ValidationError):
            OrderItemInput(product_id="not-a-uuid", quantity=1)  # type: ignore[arg-type]


class TestOrderCreateRequest:
    """Tests for OrderCreateRequest schema."""

    def test_order_create_request_valid(self) -> None:
        """Test valid OrderCreateRequest with multiple items."""
        pid1 = uuid.uuid4()
        pid2 = uuid.uuid4()
        req = OrderCreateRequest(
            items=[
                OrderItemInput(product_id=pid1, quantity=2),
                OrderItemInput(product_id=pid2, quantity=1),
            ]
        )
        assert len(req.items) == 2
        assert req.items[0].product_id == pid1
        assert req.items[1].product_id == pid2

    def test_order_create_request_empty_items_fails(self) -> None:
        """Test that empty items list raises ValidationError."""
        with pytest.raises(ValidationError):
            OrderCreateRequest(items=[])

    def test_order_create_request_duplicate_products_fails(self) -> None:
        """Test that duplicate product_id in items list is rejected."""
        pid = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            OrderCreateRequest(
                items=[
                    OrderItemInput(product_id=pid, quantity=2),
                    OrderItemInput(product_id=pid, quantity=1),
                ]
            )
        assert "Duplicate product_id" in str(exc_info.value)


class TestOrderItemResponse:
    """Tests for OrderItemResponse schema."""

    def test_order_item_response_valid(self) -> None:
        """Test OrderItemResponse direct instantiation."""
        item_id = uuid.uuid4()
        product_id = uuid.uuid4()
        res = OrderItemResponse(
            id=item_id,
            product_id=product_id,
            product_name="Cappuccino",
            quantity=2,
            unit_price=Decimal("3.00"),
            subtotal=Decimal("6.00"),
        )
        assert res.id == item_id
        assert res.product_id == product_id
        assert res.product_name == "Cappuccino"
        assert res.quantity == 2
        assert res.unit_price == Decimal("3.00")
        assert res.subtotal == Decimal("6.00")

    def test_order_item_response_from_orm(self) -> None:
        """Test OrderItemResponse model_validate converts from ORM instance."""
        product = Product(
            name="Vanilla Croissant",
            price=Decimal("3.50"),
            category=CategoryType.PASTRY,
        )
        item = OrderItem(
            id=uuid.uuid4(),
            product_id=product.id,
            quantity=3,
            unit_price=Decimal("3.50"),
        )
        item.product = product

        res = OrderItemResponse.model_validate(item)
        assert res.id == item.id
        assert res.product_id == product.id
        assert res.product_name == "Vanilla Croissant"
        assert res.quantity == 3
        assert res.unit_price == Decimal("3.50")
        assert res.subtotal == Decimal("10.50")

    def test_order_item_response_missing_fields_fails(self) -> None:
        """Test that omitting required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            OrderItemResponse(
                product_id=uuid.uuid4(),
                quantity=1,
            )  # type: ignore[call-arg]


class TestOrderResponse:
    """Tests for OrderResponse schema."""

    def test_order_response_valid(self) -> None:
        """Test OrderResponse direct instantiation."""
        order_id = uuid.uuid4()
        user_id = uuid.uuid4()
        now = datetime.now(UTC)

        items = [
            OrderItemResponse(
                id=uuid.uuid4(),
                product_id=uuid.uuid4(),
                product_name="Americano",
                quantity=1,
                unit_price=Decimal("2.50"),
                subtotal=Decimal("2.50"),
            )
        ]

        res = OrderResponse(
            id=order_id,
            user_id=user_id,
            status=OrderStatus.PENDING,
            total_amount=Decimal("2.50"),
            items=items,
            ordered_at=now,
        )

        assert res.id == order_id
        assert res.user_id == user_id
        assert res.status == OrderStatus.PENDING
        assert res.total_amount == Decimal("2.50")
        assert len(res.items) == 1
        assert res.ordered_at == now

    def test_order_response_from_orm(self) -> None:
        """Test OrderResponse model_validate converts from Order ORM instance."""
        product = Product(
            name="Espresso Double",
            price=Decimal("3.00"),
            category=CategoryType.COFFEE,
        )
        item = OrderItem(
            id=uuid.uuid4(),
            product_id=product.id,
            quantity=2,
            unit_price=Decimal("3.00"),
        )
        item.product = product

        order = Order(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            status=OrderStatus.CONFIRMED,
            total_amount=Decimal("6.00"),
        )
        order.items = [item]
        order.ordered_at = datetime.now(UTC)

        res = OrderResponse.model_validate(order)
        assert res.id == order.id
        assert res.user_id == order.user_id
        assert res.status == OrderStatus.CONFIRMED
        assert res.total_amount == Decimal("6.00")
        assert len(res.items) == 1
        assert res.items[0].product_name == "Espresso Double"
        assert res.items[0].subtotal == Decimal("6.00")


class TestOrderStatusRequest:
    """Tests for OrderStatusRequest schema."""

    def test_order_status_request_enum(self) -> None:
        """Test OrderStatusRequest with enum values."""
        req1 = OrderStatusRequest(status=OrderStatus.CONFIRMED)
        assert req1.status == OrderStatus.CONFIRMED

        req2 = OrderStatusRequest(status=OrderStatus.COMPLETED)
        assert req2.status == OrderStatus.COMPLETED

        req3 = OrderStatusRequest(status=OrderStatus.CANCELLED)
        assert req3.status == OrderStatus.CANCELLED

    def test_order_status_request_string_coercion(self) -> None:
        """Test OrderStatusRequest coercion from string."""
        req = OrderStatusRequest.model_validate({"status": "CONFIRMED"})
        assert req.status == OrderStatus.CONFIRMED

    def test_order_status_request_invalid_fails(self) -> None:
        """Test that invalid status string raises ValidationError."""
        with pytest.raises(ValidationError):
            OrderStatusRequest(status="SHIPPED")  # type: ignore[arg-type]

        with pytest.raises(ValidationError):
            OrderStatusRequest.model_validate({"status": "INVALID"})
