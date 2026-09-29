"""
tests/test_order_model.py
Unit tests for Order, OrderItem models, and OrderStatus enum.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import CategoryType, Product
from app.models.user import User


def test_order_status_enum():
    """Verify OrderStatus enum values."""
    assert OrderStatus.PENDING.value == "PENDING"
    assert OrderStatus.CONFIRMED.value == "CONFIRMED"
    assert OrderStatus.COMPLETED.value == "COMPLETED"
    assert OrderStatus.CANCELLED.value == "CANCELLED"


def test_order_defaults_and_repr():
    """Verify default field values and repr format of Order."""
    order = Order(
        total_amount=Decimal("15.50"),
    )
    assert isinstance(order.id, UUID)
    assert order.status == OrderStatus.PENDING
    assert order.total_amount == Decimal("15.50")

    order_repr = repr(order)
    assert "Order" in order_repr
    assert "total_amount=Decimal('15.50')" in order_repr


def test_order_item_subtotal_calculation():
    """Verify OrderItem subtotal calculation property."""
    item = OrderItem(
        quantity=3,
        unit_price=Decimal("4.50"),
    )
    assert isinstance(item.id, UUID)
    assert item.quantity == 3
    assert item.unit_price == Decimal("4.50")
    assert item.subtotal == Decimal("13.50")
    assert item.product_name == ""


async def test_create_order_with_items_and_relationships(
    db_session: AsyncSession,
):
    """Verify end-to-end relationships between User, Order, OrderItem, and Product."""
    user = User(
        clerk_id="user_coffee_lover",
        email="coffee_lover@cocoloco.com",
        full_name="Coffee Lover",
    )
    cappuccino = Product(
        name="Cappuccino",
        price=Decimal("3.00"),
        category=CategoryType.COFFEE,
    )
    croissant = Product(
        name="Croissant",
        price=Decimal("3.00"),
        category=CategoryType.PASTRY,
    )
    db_session.add_all([user, cappuccino, croissant])
    await db_session.commit()

    # Place an order with 2 items
    order = Order(
        user_id=user.id,
        status=OrderStatus.PENDING,
        total_amount=Decimal("9.00"),
    )
    item1 = OrderItem(
        product_id=cappuccino.id,
        quantity=2,
        unit_price=cappuccino.price,
    )
    item2 = OrderItem(
        product_id=croissant.id,
        quantity=1,
        unit_price=croissant.price,
    )
    order.items.extend([item1, item2])

    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order, ["items", "user"])

    assert order.ordered_at is not None
    assert len(order.items) == 2
    assert order.user.id == user.id

    # Verify snapshotted unit_price resilience when product price changes
    cappuccino.price = Decimal("5.00")
    await db_session.commit()
    await db_session.refresh(item1)
    # item1 snapshotted price must remain 3.00
    assert item1.unit_price == Decimal("3.00")
    assert item1.subtotal == Decimal("6.00")

    # Verify query with eager loading
    stmt = select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    result = await db_session.execute(stmt)
    loaded_order = result.scalar_one()
    assert len(loaded_order.items) == 2


async def test_order_cascade_delete(db_session: AsyncSession):
    """Verify deleting an Order cascades to its OrderItems without deleting Products."""
    user = User(
        clerk_id="user_cancel_test",
        email="cancel_test@cocoloco.com",
    )
    latte = Product(
        name="Latte Art",
        price=Decimal("4.00"),
        category=CategoryType.COFFEE,
    )
    db_session.add_all([user, latte])
    await db_session.commit()

    order = Order(
        user_id=user.id,
        total_amount=Decimal("4.00"),
    )
    item = OrderItem(
        product_id=latte.id,
        quantity=1,
        unit_price=latte.price,
    )
    order.items.append(item)
    db_session.add(order)
    await db_session.commit()

    # Delete order
    await db_session.delete(order)
    await db_session.commit()

    # Order and OrderItem should be gone
    orders_res = await db_session.execute(select(Order).where(Order.id == order.id))
    assert orders_res.scalar_one_or_none() is None

    items_res = await db_session.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    assert len(items_res.scalars().all()) == 0

    # User and Product must still exist!
    user_res = await db_session.execute(select(User).where(User.id == user.id))
    assert user_res.scalar_one_or_none() is not None

    prod_res = await db_session.execute(select(Product).where(Product.id == latte.id))
    assert prod_res.scalar_one_or_none() is not None
