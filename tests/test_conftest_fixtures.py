"""
tests/test_conftest_fixtures.py
Unit tests verifying shared test fixtures and helpers in tests/conftest.py:
- fake_user fixture (USER role, is_active=True)
- fake_admin fixture (ADMIN role, is_active=True)
- override_get_current_user helper
- test_product shared fixture
- test_order shared fixture
"""

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.main import app
from app.models.order import Order, OrderStatus
from app.models.product import CategoryType, Product
from app.models.user import User, UserRole
from tests.conftest import override_get_current_user


@pytest.mark.asyncio
async def test_fake_user_fixture(fake_user: User) -> None:
    """fake_user provides an active standard user."""
    assert fake_user.id is not None
    assert fake_user.role == UserRole.USER
    assert fake_user.is_active is True
    assert fake_user.email.endswith("@example.com")


@pytest.mark.asyncio
async def test_fake_admin_fixture(fake_admin: User) -> None:
    """fake_admin provides an active ADMIN user."""
    assert fake_admin.id is not None
    assert fake_admin.role == UserRole.ADMIN
    assert fake_admin.is_active is True
    assert fake_admin.email.endswith("@cocoloco.com")


@pytest.mark.asyncio
async def test_test_product_fixture(test_product: Product) -> None:
    """test_product provides an available catalog item."""
    assert test_product.id is not None
    assert test_product.name == "Classic Espresso"
    assert test_product.category == CategoryType.COFFEE
    assert test_product.is_available is True


@pytest.mark.asyncio
async def test_test_order_fixture(test_order: Order, fake_user: User) -> None:
    """test_order provides an order linked to fake_user with order items."""
    assert test_order.id is not None
    assert test_order.user_id == fake_user.id
    assert test_order.status == OrderStatus.PENDING
    assert len(test_order.items) == 1
    assert test_order.items[0].quantity == 2


@pytest.mark.asyncio
async def test_override_get_current_user_helper(
    client: AsyncClient,
    fake_user: User,
) -> None:
    """override_get_current_user injects user into authenticated endpoints."""
    app.dependency_overrides[get_current_user] = override_get_current_user(fake_user)
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(fake_user.id)
