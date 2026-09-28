"""
tests/test_user_model.py
Unit tests for User model, UserRole enum, and Order relationship.
"""

import uuid
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.user import User, UserRole


def test_user_role_enum():
    """Verify UserRole enum values and is_admin property."""
    assert UserRole.ADMIN.value == "ADMIN"
    assert UserRole.USER.value == "USER"
    assert UserRole.ADMIN.is_admin is True
    assert UserRole.USER.is_admin is False


def test_user_model_defaults_and_repr():
    """Verify default field values and informative __repr__ format."""
    user = User(
        clerk_id="user_clerk_123",
        email="user@cocoloco.com",
    )
    assert isinstance(user.id, UUID)
    assert user.clerk_id == "user_clerk_123"
    assert user.email == "user@cocoloco.com"
    assert user.full_name is None
    assert user.role == UserRole.USER
    assert user.is_active is True
    assert user.is_admin is False

    user_repr = repr(user)
    assert "User" in user_repr
    assert "email='user@cocoloco.com'" in user_repr
    assert "role=<UserRole.USER: 'USER'>" in user_repr


async def test_create_and_query_user(db_session: AsyncSession):
    """Verify creating and persisting a User in database."""
    user = User(
        clerk_id="user_clerk_abc",
        email="barista@cocoloco.com",
        full_name="Barista Bob",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    stmt = select(User).where(User.clerk_id == "user_clerk_abc")
    result = await db_session.execute(stmt)
    persisted_user = result.scalar_one()

    assert persisted_user.id == user.id
    assert persisted_user.email == "barista@cocoloco.com"
    assert persisted_user.full_name == "Barista Bob"
    assert persisted_user.role == UserRole.ADMIN
    assert persisted_user.is_admin is True
    assert persisted_user.created_at is not None
    assert persisted_user.updated_at is not None


async def test_user_duplicate_email_raises_integrity_error(
    db_session: AsyncSession,
):
    """Verify unique constraint on email column."""
    user1 = User(
        clerk_id="user_clerk_1",
        email="duplicate@cocoloco.com",
        full_name="User One",
    )
    user2 = User(
        clerk_id="user_clerk_2",
        email="duplicate@cocoloco.com",
        full_name="User Two",
    )
    db_session.add(user1)
    await db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_user_duplicate_clerk_id_raises_integrity_error(
    db_session: AsyncSession,
):
    """Verify unique constraint on clerk_id column."""
    user1 = User(
        clerk_id="user_same_clerk",
        email="first@cocoloco.com",
    )
    user2 = User(
        clerk_id="user_same_clerk",
        email="second@cocoloco.com",
    )
    db_session.add(user1)
    await db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_user_orders_relationship_and_cascade(db_session: AsyncSession):
    """Verify 1-to-Many relationship between User and Order and cascade delete."""
    user = User(
        clerk_id="user_order_owner",
        email="buyer@cocoloco.com",
        full_name="Buyer Ben",
    )
    order1 = Order(id=uuid.uuid4(), total_amount=Decimal("5.00"))
    order2 = Order(id=uuid.uuid4(), total_amount=Decimal("10.00"))
    user.orders.extend([order1, order2])

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user, ["orders"])

    assert len(user.orders) == 2
    assert order1.user_id == user.id
    assert order2.user_id == user.id
    assert order1.user == user

    # Query with selectinload to verify explicit eager loading
    stmt = select(User).where(User.id == user.id).options(selectinload(User.orders))
    result = await db_session.execute(stmt)
    loaded_user = result.scalar_one()
    assert len(loaded_user.orders) == 2

    # Test cascade delete: deleting user should delete their orders
    await db_session.delete(user)
    await db_session.commit()

    orders_stmt = select(Order).where(Order.user_id == user.id)
    orders_result = await db_session.execute(orders_stmt)
    assert len(orders_result.scalars().all()) == 0
