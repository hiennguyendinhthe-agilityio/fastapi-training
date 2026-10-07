"""
tests/api/test_orders.py
Integration and unit tests for Orders API endpoints:
- POST /api/v1/orders (Place order with price snapshotting and availability check)
- GET /api/v1/orders/me (Paginated personal order history)
- GET /api/v1/orders/{id} (Order detail: owner or admin)
- GET /api/v1/orders (Admin-only platform order listing)
- PATCH /api/v1/orders/{id}/status (Admin-only order status transition)
- OpenAPI endpoint aggregation verification
"""

import uuid
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.api.v1.orders import (
    create_order,
    get_order_by_id,
    list_all_orders,
    list_my_orders,
    update_order_status,
)
from app.main import app
from app.models.order import OrderStatus
from app.models.product import CategoryType, Product
from app.models.user import User, UserRole
from app.schemas.order import (
    OrderCreateRequest,
    OrderItemInput,
    OrderStatusRequest,
)


def _override_user(user: User) -> Any:
    """Return a dependency override callable that returns the given user."""

    async def _inner() -> User:
        return user

    return _inner


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create and return an active ADMIN user."""
    admin = User(
        clerk_id=f"clerk_admin_{uuid.uuid4().hex[:8]}",
        email=f"admin_{uuid.uuid4().hex[:6]}@cocoloco.com",
        full_name="Head Barista",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def customer_one(db_session: AsyncSession) -> User:
    """Create and return first active customer."""
    user = User(
        clerk_id=f"clerk_cust1_{uuid.uuid4().hex[:8]}",
        email=f"cust1_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Customer Alice",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def customer_two(db_session: AsyncSession) -> User:
    """Create and return second active customer."""
    user = User(
        clerk_id=f"clerk_cust2_{uuid.uuid4().hex[:8]}",
        email=f"cust2_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Customer Bob",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def deactivated_customer(db_session: AsyncSession) -> User:
    """Create and return a deactivated customer."""
    user = User(
        clerk_id=f"clerk_deact_{uuid.uuid4().hex[:8]}",
        email=f"deact_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Deactivated Dan",
        role=UserRole.USER,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_products(db_session: AsyncSession) -> dict[str, Product]:
    """Create catalog items for testing."""
    latte = Product(
        name="Vanilla Latte",
        description="Espresso with vanilla syrup",
        price=Decimal("4.50"),
        category=CategoryType.COFFEE,
        is_available=True,
    )
    muffin = Product(
        name="Blueberry Muffin",
        description="Freshly baked muffin",
        price=Decimal("3.50"),
        category=CategoryType.PASTRY,
        is_available=True,
    )
    seasonal_pie = Product(
        name="Pumpkin Pie",
        description="Limited seasonal pie",
        price=Decimal("5.00"),
        category=CategoryType.SEASONAL,
        is_available=False,  # Sold out
    )
    db_session.add_all([latte, muffin, seasonal_pie])
    await db_session.commit()
    for p in (latte, muffin, seasonal_pie):
        await db_session.refresh(p)
    return {"latte": latte, "muffin": muffin, "seasonal_pie": seasonal_pie}


# ---------------------------------------------------------------------------
# OpenAPI & Aggregator Verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_aggregator_openapi_schema(client: AsyncClient) -> None:
    """Task 6.4: Verify all v1 endpoints appear on OpenAPI schema."""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]

    # Verify auth
    assert "/api/v1/auth/sync" in paths
    # Verify users
    assert "/api/v1/users/me" in paths
    assert "/api/v1/users" in paths
    assert "/api/v1/users/{id}/status" in paths
    # Verify products
    assert "/api/v1/products" in paths
    assert "/api/v1/products/{id}" in paths
    # Verify orders
    assert "/api/v1/orders" in paths
    assert "/api/v1/orders/me" in paths
    assert "/api/v1/orders/{id}" in paths
    assert "/api/v1/orders/{id}/status" in paths


# ---------------------------------------------------------------------------
# POST /api/v1/orders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_order_happy_path(
    client: AsyncClient,
    customer_one: User,
    sample_products: dict[str, Product],
) -> None:
    """Customer places order; prices and total are calculated server-side."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]
    muffin = sample_products["muffin"]

    payload = {
        "items": [
            {"product_id": str(latte.id), "quantity": 2},
            {"product_id": str(muffin.id), "quantity": 1},
        ]
    }

    resp = await client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["user_id"] == str(customer_one.id)
    assert data["status"] == "PENDING"
    # 2 * 4.50 + 1 * 3.50 = 12.50
    assert Decimal(data["total_amount"]) == Decimal("12.50")
    assert len(data["items"]) == 2

    # Check line item details
    items_by_pid = {item["product_id"]: item for item in data["items"]}
    latte_item = items_by_pid[str(latte.id)]
    assert latte_item["product_name"] == "Vanilla Latte"
    assert latte_item["quantity"] == 2
    assert Decimal(latte_item["unit_price"]) == Decimal("4.50")
    assert Decimal(latte_item["subtotal"]) == Decimal("9.00")

    muffin_item = items_by_pid[str(muffin.id)]
    assert muffin_item["product_name"] == "Blueberry Muffin"
    assert muffin_item["quantity"] == 1
    assert Decimal(muffin_item["unit_price"]) == Decimal("3.50")
    assert Decimal(muffin_item["subtotal"]) == Decimal("3.50")


@pytest.mark.asyncio
async def test_create_order_unauthenticated(client: AsyncClient) -> None:
    """Missing auth token returns 401."""
    resp = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(uuid.uuid4()), "quantity": 1}]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_order_nonexistent_product_returns_404(
    client: AsyncClient,
    customer_one: User,
) -> None:
    """Ordering non-existent product returns 404 Not Found."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    missing_id = uuid.uuid4()
    payload = {"items": [{"product_id": str(missing_id), "quantity": 1}]}

    resp = await client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 404
    assert f"'{missing_id}' not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_order_unavailable_product_returns_400(
    client: AsyncClient,
    customer_one: User,
    sample_products: dict[str, Product],
) -> None:
    """Ordering unavailable/sold-out product returns 400 Bad Request."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    pie = sample_products["seasonal_pie"]
    payload = {"items": [{"product_id": str(pie.id), "quantity": 1}]}

    resp = await client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 400
    assert "Pumpkin Pie" in resp.json()["detail"]
    assert "unavailable" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_order_validation_duplicate_products(
    client: AsyncClient,
    customer_one: User,
    sample_products: dict[str, Product],
) -> None:
    """Sending duplicate product_id in items returns 422 Unprocessable Entity."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]
    payload = {
        "items": [
            {"product_id": str(latte.id), "quantity": 1},
            {"product_id": str(latte.id), "quantity": 2},
        ]
    }

    resp = await client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_order_validation_empty_items(
    client: AsyncClient,
    customer_one: User,
) -> None:
    """Sending empty items array returns 422."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    resp = await client.post("/api/v1/orders", json={"items": []})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_order_validation_invalid_quantity(
    client: AsyncClient,
    customer_one: User,
    sample_products: dict[str, Product],
) -> None:
    """Sending quantity < 1 returns 422 Unprocessable Entity."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]

    # quantity 0
    resp_zero = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 0}]},
    )
    assert resp_zero.status_code == 422

    # negative quantity
    resp_neg = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": -3}]},
    )
    assert resp_neg.status_code == 422


@pytest.mark.asyncio
async def test_create_order_price_snapshot_invariance(
    client: AsyncClient,
    customer_one: User,
    sample_products: dict[str, Product],
    db_session: AsyncSession,
) -> None:
    """Snapshotted unit_price does not drift when product price changes later."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]

    # 1. Place order when price is 4.50
    create_resp = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 1}]},
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    # 2. Modify product price in database to 9.99
    latte.price = Decimal("9.99")
    db_session.add(latte)
    await db_session.commit()

    # 3. Retrieve order and verify price has NOT changed
    get_resp = await client.get(f"/api/v1/orders/{order_id}")
    assert get_resp.status_code == 200
    order_data = get_resp.json()
    assert Decimal(order_data["total_amount"]) == Decimal("4.50")
    assert Decimal(order_data["items"][0]["unit_price"]) == Decimal("4.50")
    assert Decimal(order_data["items"][0]["subtotal"]) == Decimal("4.50")


# ---------------------------------------------------------------------------
# GET /api/v1/orders/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_my_orders_happy_path(
    client: AsyncClient,
    customer_one: User,
    customer_two: User,
    sample_products: dict[str, Product],
) -> None:
    """Customer sees only their own order history with pagination."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]

    # Place 2 orders for customer 1
    await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 1}]},
    )
    await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 2}]},
    )

    # Place 1 order for customer 2
    app.dependency_overrides[get_current_user] = _override_user(customer_two)
    await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 3}]},
    )

    # Check customer 1 history
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    resp = await client.get("/api/v1/orders/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    for order in data["items"]:
        assert order["user_id"] == str(customer_one.id)

    # Check customer 2 history
    app.dependency_overrides[get_current_user] = _override_user(customer_two)
    resp2 = await client.get("/api/v1/orders/me")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total"] == 1
    assert len(data2["items"]) == 1
    assert data2["items"][0]["user_id"] == str(customer_two.id)


@pytest.mark.asyncio
async def test_list_my_orders_unauthenticated(client: AsyncClient) -> None:
    """Missing auth token on /me returns 401."""
    resp = await client.get("/api/v1/orders/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/orders/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_order_detail_by_owner(
    client: AsyncClient,
    customer_one: User,
    sample_products: dict[str, Product],
) -> None:
    """Customer can view their own order detail."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]
    create_resp = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 1}]},
    )
    order_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/orders/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


@pytest.mark.asyncio
async def test_get_order_detail_by_admin(
    client: AsyncClient,
    customer_one: User,
    admin_user: User,
    sample_products: dict[str, Product],
) -> None:
    """Admin can view any customer's order detail."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]
    create_resp = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 1}]},
    )
    order_id = create_resp.json()["id"]

    # Switch to admin
    app.dependency_overrides[get_current_user] = _override_user(admin_user)
    resp = await client.get(f"/api/v1/orders/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


@pytest.mark.asyncio
async def test_get_order_detail_forbidden_for_other_customer(
    client: AsyncClient,
    customer_one: User,
    customer_two: User,
    sample_products: dict[str, Product],
) -> None:
    """Customer two cannot view customer one's order (403 Forbidden)."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]
    create_resp = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 1}]},
    )
    order_id = create_resp.json()["id"]

    # Switch to customer two
    app.dependency_overrides[get_current_user] = _override_user(customer_two)
    resp = await client.get(f"/api/v1/orders/{order_id}")
    assert resp.status_code == 403
    assert "permission" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_order_detail_not_found(
    client: AsyncClient,
    customer_one: User,
) -> None:
    """Non-existent order UUID returns 404."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    resp = await client.get(f"/api/v1/orders/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/orders (Admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_all_orders_admin_success(
    client: AsyncClient,
    customer_one: User,
    customer_two: User,
    admin_user: User,
    sample_products: dict[str, Product],
) -> None:
    """Admin can list all platform orders across all customers."""
    latte = sample_products["latte"]

    # Create order for customer 1
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 1}]},
    )

    # Create order for customer 2
    app.dependency_overrides[get_current_user] = _override_user(customer_two)
    await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 1}]},
    )

    # Query all orders as Admin
    app.dependency_overrides[require_admin] = _override_user(admin_user)
    resp = await client.get("/api/v1/orders")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_all_orders_forbidden_for_regular_user(
    client: AsyncClient,
    customer_one: User,
) -> None:
    """Regular user cannot list all orders (403 Forbidden)."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    # require_admin is NOT overridden to admin
    resp = await client.get("/api/v1/orders")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/v1/orders/{id}/status (Admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_order_status_admin_success(
    client: AsyncClient,
    customer_one: User,
    admin_user: User,
    sample_products: dict[str, Product],
) -> None:
    """Admin successfully updates order status to CONFIRMED and COMPLETED."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]
    create_resp = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 1}]},
    )
    order_id = create_resp.json()["id"]

    # Admin updates status
    app.dependency_overrides[require_admin] = _override_user(admin_user)
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CONFIRMED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"

    # Admin updates status to COMPLETED
    resp2 = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "COMPLETED"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_update_order_status_forbidden_for_customer(
    client: AsyncClient,
    customer_one: User,
    sample_products: dict[str, Product],
) -> None:
    """Regular customer cannot update order status (403 Forbidden)."""
    app.dependency_overrides[get_current_user] = _override_user(customer_one)
    latte = sample_products["latte"]
    create_resp = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(latte.id), "quantity": 1}]},
    )
    order_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CONFIRMED"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_order_status_not_found(
    client: AsyncClient,
    admin_user: User,
) -> None:
    """Updating status of non-existent order returns 404."""
    app.dependency_overrides[require_admin] = _override_user(admin_user)
    resp = await client.patch(
        f"/api/v1/orders/{uuid.uuid4()}/status",
        json={"status": "CONFIRMED"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Direct router function unit tests for complete code coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_direct_router_create_order(
    db_session: AsyncSession,
    customer_one: User,
    sample_products: dict[str, Product],
) -> None:
    """Directly execute create_order handler."""
    latte = sample_products["latte"]
    payload = OrderCreateRequest(
        items=[OrderItemInput(product_id=latte.id, quantity=1)]
    )
    resp = await create_order(payload, customer_one, db_session)
    assert resp.user_id == customer_one.id
    assert resp.total_amount == Decimal("4.50")


@pytest.mark.asyncio
async def test_direct_router_create_order_errors(
    db_session: AsyncSession,
    customer_one: User,
    sample_products: dict[str, Product],
) -> None:
    """Directly test exceptions in create_order."""
    missing_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_404:
        await create_order(
            OrderCreateRequest(
                items=[OrderItemInput(product_id=missing_id, quantity=1)]
            ),
            customer_one,
            db_session,
        )
    assert exc_404.value.status_code == 404

    pie = sample_products["seasonal_pie"]
    with pytest.raises(HTTPException) as exc_400:
        await create_order(
            OrderCreateRequest(items=[OrderItemInput(product_id=pie.id, quantity=1)]),
            customer_one,
            db_session,
        )
    assert exc_400.value.status_code == 400


@pytest.mark.asyncio
async def test_direct_router_list_and_get(
    db_session: AsyncSession,
    customer_one: User,
    customer_two: User,
    admin_user: User,
    sample_products: dict[str, Product],
) -> None:
    """Directly test list_my_orders, get_by_id, list_all, update_status."""
    latte = sample_products["latte"]
    order_dto = await create_order(
        OrderCreateRequest(items=[OrderItemInput(product_id=latte.id, quantity=1)]),
        customer_one,
        db_session,
    )

    # list_my_orders
    my_orders = await list_my_orders(customer_one, db_session, page=1, size=10)
    assert my_orders.total == 1

    # get_order_by_id (owner)
    detail = await get_order_by_id(order_dto.id, customer_one, db_session)
    assert detail.id == order_dto.id

    # get_order_by_id (admin)
    detail_admin = await get_order_by_id(order_dto.id, admin_user, db_session)
    assert detail_admin.id == order_dto.id

    # get_order_by_id (forbidden customer)
    with pytest.raises(HTTPException) as exc_403:
        await get_order_by_id(order_dto.id, customer_two, db_session)
    assert exc_403.value.status_code == 403

    # get_order_by_id (404)
    with pytest.raises(HTTPException) as exc_404:
        await get_order_by_id(uuid.uuid4(), customer_one, db_session)
    assert exc_404.value.status_code == 404

    # list_all_orders
    all_orders = await list_all_orders(admin_user, db_session, page=1, size=10)
    assert all_orders.total == 1

    # update_order_status
    updated = await update_order_status(
        order_dto.id,
        OrderStatusRequest(status=OrderStatus.CONFIRMED),
        admin_user,
        db_session,
    )
    assert updated.status == OrderStatus.CONFIRMED

    # update_order_status (404)
    with pytest.raises(HTTPException) as exc_patch_404:
        await update_order_status(
            uuid.uuid4(),
            OrderStatusRequest(status=OrderStatus.CONFIRMED),
            admin_user,
            db_session,
        )
    assert exc_patch_404.value.status_code == 404
