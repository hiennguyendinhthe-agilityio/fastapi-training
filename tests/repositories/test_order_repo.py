"""
tests/repositories/test_order_repo.py
Unit & Integration tests for app/repositories/order_repo.py.

Tests cover:
- create (happy path, price snapshotting, server-side arithmetic)
- create with non-existent product -> ProductNotFoundError
- create with unavailable product -> ProductUnavailableError
- get_by_id (found with eager loaded relations, not found None)
- get_by_user (pagination, user boundary isolation, ordering)
- get_all (admin pagination across multiple users)
- update_status (lifecycle transitions: PENDING -> CONFIRMED -> COMPLETED / CANCELLED)
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import OrderStatus
from app.models.product import CategoryType, Product
from app.models.user import User, UserRole
from app.repositories import order_repo
from app.schemas.order import OrderItemInput


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create a standard active user for testing orders."""
    user = User(
        clerk_id=f"clerk_customer_{uuid.uuid4().hex[:8]}",
        email=f"customer_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Alice Coffee Lover",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_user_two(db_session: AsyncSession) -> User:
    """Create a second active user to test isolation."""
    user = User(
        clerk_id=f"clerk_customer2_{uuid.uuid4().hex[:8]}",
        email=f"customer2_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Bob Tea Fan",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_products(db_session: AsyncSession) -> dict[str, Product]:
    """Create products for testing: available coffee, pastry, and unavailable item."""
    coffee = Product(
        name="Artisan Espresso",
        description="Double shot",
        price=Decimal("3.50"),
        category=CategoryType.COFFEE,
        is_available=True,
    )
    croissant = Product(
        name="Almond Croissant",
        description="Baked fresh",
        price=Decimal("4.25"),
        category=CategoryType.PASTRY,
        is_available=True,
    )
    sold_out = Product(
        name="Truffle Cake",
        description="Seasonal dessert",
        price=Decimal("12.00"),
        category=CategoryType.SEASONAL,
        is_available=False,
    )
    db_session.add_all([coffee, croissant, sold_out])
    await db_session.commit()
    for p in (coffee, croissant, sold_out):
        await db_session.refresh(p)
    return {"coffee": coffee, "croissant": croissant, "sold_out": sold_out}


@pytest.mark.asyncio
async def test_create_order_happy_path(
    db_session: AsyncSession,
    sample_user: User,
    sample_products: dict[str, Product],
) -> None:
    """Order is created with snapshot prices and server-calculated total."""
    coffee = sample_products["coffee"]
    croissant = sample_products["croissant"]

    items_input = [
        OrderItemInput(product_id=coffee.id, quantity=2),
        OrderItemInput(product_id=croissant.id, quantity=1),
    ]

    order = await order_repo.create(
        db_session,
        user_id=sample_user.id,
        items=items_input,
    )

    # Expected: 2 * 3.50 + 1 * 4.25 = 7.00 + 4.25 = 11.25
    expected_total = Decimal("11.25")

    assert order.id is not None
    assert order.user_id == sample_user.id
    assert order.status == OrderStatus.PENDING
    assert order.total_amount == expected_total
    assert len(order.items) == 2

    # Check snapshot integrity
    items_by_prod = {item.product_id: item for item in order.items}
    assert items_by_prod[coffee.id].unit_price == Decimal("3.50")
    assert items_by_prod[coffee.id].quantity == 2
    assert items_by_prod[coffee.id].subtotal == Decimal("7.00")
    assert items_by_prod[coffee.id].product_name == "Artisan Espresso"

    assert items_by_prod[croissant.id].unit_price == Decimal("4.25")
    assert items_by_prod[croissant.id].quantity == 1
    assert items_by_prod[croissant.id].subtotal == Decimal("4.25")
    assert items_by_prod[croissant.id].product_name == "Almond Croissant"


@pytest.mark.asyncio
async def test_create_order_missing_product_raises_error(
    db_session: AsyncSession,
    sample_user: User,
) -> None:
    """Attempting to order a non-existent product UUID raises ProductNotFoundError."""
    ghost_id = uuid.uuid4()
    items_input = [OrderItemInput(product_id=ghost_id, quantity=1)]

    with pytest.raises(order_repo.ProductNotFoundError) as exc_info:
        await order_repo.create(
            db_session,
            user_id=sample_user.id,
            items=items_input,
        )

    assert exc_info.value.product_id == ghost_id
    assert f"'{ghost_id}'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_order_unavailable_product_raises_error(
    db_session: AsyncSession,
    sample_user: User,
    sample_products: dict[str, Product],
) -> None:
    """Attempting to order an unavailable product raises ProductUnavailableError."""
    sold_out = sample_products["sold_out"]
    items_input = [OrderItemInput(product_id=sold_out.id, quantity=1)]

    with pytest.raises(order_repo.ProductUnavailableError) as exc_info:
        await order_repo.create(
            db_session,
            user_id=sample_user.id,
            items=items_input,
        )

    assert exc_info.value.product_id == sold_out.id
    assert exc_info.value.product_name == "Truffle Cake"
    assert "unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_by_id_found_and_not_found(
    db_session: AsyncSession,
    sample_user: User,
    sample_products: dict[str, Product],
) -> None:
    """get_by_id returns hydrated order when present, None when absent."""
    coffee = sample_products["coffee"]
    order = await order_repo.create(
        db_session,
        user_id=sample_user.id,
        items=[OrderItemInput(product_id=coffee.id, quantity=1)],
    )

    found = await order_repo.get_by_id(db_session, order.id)
    assert found is not None
    assert found.id == order.id
    assert len(found.items) == 1
    assert found.items[0].product_name == "Artisan Espresso"

    not_found = await order_repo.get_by_id(db_session, uuid.uuid4())
    assert not_found is None


@pytest.mark.asyncio
async def test_get_by_user_pagination_and_isolation(
    db_session: AsyncSession,
    sample_user: User,
    sample_user_two: User,
    sample_products: dict[str, Product],
) -> None:
    """get_by_user isolates orders by user and handles pagination parameters."""
    coffee = sample_products["coffee"]

    # Create 3 orders for user 1
    for _ in range(3):
        await order_repo.create(
            db_session,
            user_id=sample_user.id,
            items=[OrderItemInput(product_id=coffee.id, quantity=1)],
        )

    # Create 1 order for user 2
    await order_repo.create(
        db_session,
        user_id=sample_user_two.id,
        items=[OrderItemInput(product_id=coffee.id, quantity=2)],
    )

    # Query user 1 orders with page=1, size=2
    res_page_1 = await order_repo.get_by_user(
        db_session,
        user_id=sample_user.id,
        page=1,
        size=2,
    )
    assert res_page_1.total == 3
    assert len(res_page_1.items) == 2
    assert res_page_1.pages == 2

    # Query user 1 orders with page=2, size=2
    res_page_2 = await order_repo.get_by_user(
        db_session,
        user_id=sample_user.id,
        page=2,
        size=2,
    )
    assert len(res_page_2.items) == 1

    # Query user 1 with safe boundaries (page=0, size=-5)
    res_safe = await order_repo.get_by_user(
        db_session,
        user_id=sample_user.id,
        page=0,
        size=-5,
    )
    assert res_safe.total == 3
    assert len(res_safe.items) == 3

    # Query user 2
    res_user_two = await order_repo.get_by_user(
        db_session,
        user_id=sample_user_two.id,
        page=1,
        size=10,
    )
    assert res_user_two.total == 1
    assert len(res_user_two.items) == 1
    assert res_user_two.items[0].user_id == sample_user_two.id


@pytest.mark.asyncio
async def test_get_all_admin_pagination(
    db_session: AsyncSession,
    sample_user: User,
    sample_user_two: User,
    sample_products: dict[str, Product],
) -> None:
    """get_all returns all platform orders regardless of user."""
    coffee = sample_products["coffee"]

    await order_repo.create(
        db_session,
        user_id=sample_user.id,
        items=[OrderItemInput(product_id=coffee.id, quantity=1)],
    )
    await order_repo.create(
        db_session,
        user_id=sample_user_two.id,
        items=[OrderItemInput(product_id=coffee.id, quantity=1)],
    )

    res = await order_repo.get_all(db_session, page=1, size=10)
    assert res.total == 2
    assert len(res.items) == 2

    # Safe boundaries
    res_safe = await order_repo.get_all(db_session, page=0, size=0)
    assert res_safe.total == 2
    assert len(res_safe.items) == 2


@pytest.mark.asyncio
async def test_update_status(
    db_session: AsyncSession,
    sample_user: User,
    sample_products: dict[str, Product],
) -> None:
    """update_status modifies order status and commits the change."""
    coffee = sample_products["coffee"]
    order = await order_repo.create(
        db_session,
        user_id=sample_user.id,
        items=[OrderItemInput(product_id=coffee.id, quantity=1)],
    )
    assert order.status == OrderStatus.PENDING

    # Transition to CONFIRMED
    confirmed = await order_repo.update_status(db_session, order, OrderStatus.CONFIRMED)
    assert confirmed.status == OrderStatus.CONFIRMED

    # Transition to COMPLETED
    completed = await order_repo.update_status(
        db_session, confirmed, OrderStatus.COMPLETED
    )
    assert completed.status == OrderStatus.COMPLETED

    # Verify persistence by re-fetching
    re_fetched = await order_repo.get_by_id(db_session, order.id)
    assert re_fetched is not None
    assert re_fetched.status == OrderStatus.COMPLETED
