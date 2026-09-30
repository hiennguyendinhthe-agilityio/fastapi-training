"""
tests/api/test_products.py
Integration tests for Product API endpoints:
- GET /api/v1/products (public catalog with pagination & category filter)
- GET /api/v1/products/{id} (public product detail)
- POST /api/v1/products (admin-only creation)
- PUT /api/v1/products/{id} (admin-only update)
- DELETE /api/v1/products/{id} (admin-only deletion)
"""

import uuid
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.api.v1.products import (
    delete_product,
    get_product,
    update_product,
)
from app.main import app
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import CategoryType, Product
from app.models.user import User, UserRole
from app.schemas.product import ProductUpdateRequest


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
        full_name="Admin Chef",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create and return an active standard USER."""
    user = User(
        clerk_id=f"clerk_user_{uuid.uuid4().hex[:8]}",
        email=f"user_{uuid.uuid4().hex[:6]}@cocoloco.com",
        full_name="Regular Customer",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# GET /api/v1/products (Public)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient) -> None:
    """GET /products returns empty PageResponse when no products exist."""
    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["size"] == 10
    assert data["pages"] == 0


@pytest.mark.asyncio
async def test_list_products_populated_and_filtered(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /products supports pagination and category filtering."""
    db_session.add_all(
        [
            Product(
                name="Espresso",
                price=Decimal("2.50"),
                category=CategoryType.COFFEE,
                is_available=True,
            ),
            Product(
                name="Cappuccino",
                price=Decimal("3.50"),
                category=CategoryType.COFFEE,
                is_available=True,
            ),
            Product(
                name="Butter Croissant",
                price=Decimal("3.00"),
                category=CategoryType.PASTRY,
                is_available=True,
            ),
        ]
    )
    await db_session.commit()

    # 1. Fetch all
    res_all = await client.get("/api/v1/products")
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] == 3
    assert len(data_all["items"]) == 3

    # 2. Filter by category=coffee
    res_coffee = await client.get("/api/v1/products?category=coffee")
    assert res_coffee.status_code == 200
    data_coffee = res_coffee.json()
    assert data_coffee["total"] == 2
    assert len(data_coffee["items"]) == 2
    assert all(item["category"] == "coffee" for item in data_coffee["items"])

    # 3. Filter by category=pastry
    res_pastry = await client.get("/api/v1/products?category=pastry")
    assert res_pastry.status_code == 200
    data_pastry = res_pastry.json()
    assert data_pastry["total"] == 1
    assert data_pastry["items"][0]["name"] == "Butter Croissant"


@pytest.mark.asyncio
async def test_list_products_invalid_pagination(client: AsyncClient) -> None:
    """GET /products validates page >= 1 and size between 1 and 100."""
    res_page = await client.get("/api/v1/products?page=0")
    assert res_page.status_code == 422

    res_size = await client.get("/api/v1/products?size=101")
    assert res_size.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/products/{id} (Public)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_product_detail_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /products/{id} returns product details when ID exists."""
    product = Product(
        name="Signature Pour",
        description="Freshly brewed single origin",
        price=Decimal("4.25"),
        category=CategoryType.COFFEE,
        image_url="https://images.unsplash.com/coffee.jpg",
        is_available=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    response = await client.get(f"/api/v1/products/{product.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(product.id)
    assert data["name"] == "Signature Pour"
    assert data["price"] == "4.25"
    assert data["category"] == "coffee"
    assert data["is_available"] is True


@pytest.mark.asyncio
async def test_get_product_detail_not_found(client: AsyncClient) -> None:
    """GET /products/{id} returns 404 for non-existent product UUID."""
    random_id = uuid.uuid4()
    response = await client.get(f"/api/v1/products/{random_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


@pytest.mark.asyncio
async def test_get_product_detail_invalid_uuid(client: AsyncClient) -> None:
    """GET /products/{id} returns 422 for malformed UUID string."""
    response = await client.get("/api/v1/products/not-a-valid-uuid")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/products (Admin Only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_product_as_admin_success(
    client: AsyncClient,
    admin_user: User,
) -> None:
    """POST /products creates product when caller has ADMIN role."""
    app.dependency_overrides[require_admin] = _override_user(admin_user)
    payload = {
        "name": "Artisan Bagel",
        "description": "Toasted bagel with cream cheese",
        "price": "3.50",
        "category": "pastry",
        "image_url": "https://images.unsplash.com/bagel.jpg",
        "is_available": True,
    }
    try:
        response = await client.post("/api/v1/products", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Artisan Bagel"
        assert data["price"] == "3.50"
        assert data["category"] == "pastry"
        assert data["is_available"] is True
        assert "id" in data
        assert "created_at" in data
    finally:
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_create_product_unauthenticated_fails(client: AsyncClient) -> None:
    """POST /products returns 401 when no Bearer token is provided."""
    payload = {
        "name": "Unauthorized Coffee",
        "price": "3.00",
        "category": "coffee",
    }
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_product_as_regular_user_fails(
    client: AsyncClient,
    regular_user: User,
) -> None:
    """POST /products returns 403 when authenticated caller is not an ADMIN."""
    # Wire get_current_user to return a regular user, allowing require_admin
    # to check role
    app.dependency_overrides[get_current_user] = _override_user(regular_user)
    payload = {
        "name": "Regular User Coffee",
        "price": "3.00",
        "category": "coffee",
    }
    try:
        response = await client.post("/api/v1/products", json=payload)
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_product_validation_error(
    client: AsyncClient,
    admin_user: User,
) -> None:
    """POST /products returns 422 for negative price or empty name."""
    app.dependency_overrides[require_admin] = _override_user(admin_user)
    try:
        # Negative price
        res_price = await client.post(
            "/api/v1/products",
            json={"name": "Cheap", "price": "-1.00", "category": "coffee"},
        )
        assert res_price.status_code == 422

        # Empty name
        res_name = await client.post(
            "/api/v1/products",
            json={"name": "   ", "price": "3.00", "category": "coffee"},
        )
        assert res_name.status_code == 422
    finally:
        app.dependency_overrides.pop(require_admin, None)


# ---------------------------------------------------------------------------
# PUT /api/v1/products/{id} (Admin Only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_product_as_admin_success(
    client: AsyncClient,
    admin_user: User,
    db_session: AsyncSession,
) -> None:
    """PUT /products/{id} updates product fields when caller is ADMIN."""
    product = Product(
        name="Latte Original",
        price=Decimal("3.50"),
        category=CategoryType.COFFEE,
        is_available=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    app.dependency_overrides[require_admin] = _override_user(admin_user)
    payload = {
        "name": "Iced Vanilla Latte",
        "price": "4.25",
        "is_available": False,
    }
    try:
        response = await client.put(f"/api/v1/products/{product.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Iced Vanilla Latte"
        assert data["price"] == "4.25"
        assert data["is_available"] is False
        assert data["category"] == "coffee"  # unchanged
    finally:
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_update_product_not_found(
    client: AsyncClient,
    admin_user: User,
) -> None:
    """PUT /products/{id} returns 404 for non-existent product UUID."""
    app.dependency_overrides[require_admin] = _override_user(admin_user)
    random_id = uuid.uuid4()
    try:
        response = await client.put(
            f"/api/v1/products/{random_id}",
            json={"name": "Ghost Item"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"
    finally:
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_update_product_as_regular_user_fails(
    client: AsyncClient,
    regular_user: User,
    db_session: AsyncSession,
) -> None:
    """PUT /products/{id} returns 403 for non-admin user."""
    product = Product(
        name="Pastry",
        price=Decimal("2.00"),
        category=CategoryType.PASTRY,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    app.dependency_overrides[get_current_user] = _override_user(regular_user)
    try:
        response = await client.put(
            f"/api/v1/products/{product.id}",
            json={"price": "2.50"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# DELETE /api/v1/products/{id} (Admin Only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_product_as_admin_success(
    client: AsyncClient,
    admin_user: User,
    db_session: AsyncSession,
) -> None:
    """DELETE /products/{id} removes product and returns 204 No Content."""
    product = Product(
        name="Delete Me Coffee",
        price=Decimal("1.50"),
        category=CategoryType.COFFEE,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    product_id = product.id

    app.dependency_overrides[require_admin] = _override_user(admin_user)
    try:
        response = await client.delete(f"/api/v1/products/{product_id}")
        assert response.status_code == 204
        assert response.content == b""

        # Verify query returns 404
        res_get = await client.get(f"/api/v1/products/{product_id}")
        assert res_get.status_code == 404
    finally:
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_delete_product_not_found(
    client: AsyncClient,
    admin_user: User,
) -> None:
    """DELETE /products/{id} returns 404 for non-existent product UUID."""
    app.dependency_overrides[require_admin] = _override_user(admin_user)
    random_id = uuid.uuid4()
    try:
        response = await client.delete(f"/api/v1/products/{random_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"
    finally:
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_delete_product_as_regular_user_fails(
    client: AsyncClient,
    regular_user: User,
    db_session: AsyncSession,
) -> None:
    """DELETE /products/{id} returns 403 for non-admin user."""
    product = Product(
        name="Protected Croissant",
        price=Decimal("3.00"),
        category=CategoryType.PASTRY,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    app.dependency_overrides[get_current_user] = _override_user(regular_user)
    try:
        response = await client.delete(f"/api/v1/products/{product.id}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_delete_product_with_existing_orders_returns_409(
    client: AsyncClient,
    admin_user: User,
    regular_user: User,
    db_session: AsyncSession,
) -> None:
    """
    DELETE /products/{id} returns 409 Conflict when product is referenced in
    order_items.
    """
    product = Product(
        name="Popular Latte",
        price=Decimal("4.50"),
        category=CategoryType.COFFEE,
        is_available=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    order = Order(
        user_id=regular_user.id,
        status=OrderStatus.PENDING,
        total_amount=Decimal("4.50"),
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=Decimal("4.50"),
    )
    db_session.add(item)
    await db_session.commit()

    app.dependency_overrides[require_admin] = _override_user(admin_user)
    try:
        response = await client.delete(f"/api/v1/products/{product.id}")
        assert response.status_code == 409
        data = response.json()
        assert "associated orders" in data["detail"]
    finally:
        app.dependency_overrides.pop(require_admin, None)


# ---------------------------------------------------------------------------
# Direct Handler Invocation Tests (Coverage Completeness)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_direct_get_product_handler(db_session: AsyncSession) -> None:
    """Direct invocation of get_product router handler."""
    product = Product(
        name="Direct Pour",
        price=Decimal("4.00"),
        category=CategoryType.COFFEE,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    res = await get_product(id=product.id, db=db_session)
    assert res.id == product.id

    with pytest.raises(HTTPException) as exc_info:
        await get_product(id=uuid.uuid4(), db=db_session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Product not found"


@pytest.mark.asyncio
async def test_direct_update_product_handler(
    db_session: AsyncSession,
    admin_user: User,
) -> None:
    """Direct invocation of update_product router handler."""
    product = Product(
        name="Direct Update",
        price=Decimal("4.00"),
        category=CategoryType.COFFEE,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    updated = await update_product(
        id=product.id,
        payload=ProductUpdateRequest(price=Decimal("4.50")),
        _=admin_user,
        db=db_session,
    )
    assert updated.price == Decimal("4.50")

    with pytest.raises(HTTPException) as exc_info:
        await update_product(
            id=uuid.uuid4(),
            payload=ProductUpdateRequest(name="Ghost"),
            _=admin_user,
            db=db_session,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Product not found"


@pytest.mark.asyncio
async def test_direct_delete_product_handler(
    db_session: AsyncSession,
    admin_user: User,
) -> None:
    """Direct invocation of delete_product router handler."""
    product = Product(
        name="Direct Delete",
        price=Decimal("2.00"),
        category=CategoryType.PASTRY,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    res = await delete_product(id=product.id, _=admin_user, db=db_session)
    assert res.status_code == 204

    with pytest.raises(HTTPException) as exc_info:
        await delete_product(id=uuid.uuid4(), _=admin_user, db=db_session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Product not found"


@pytest.mark.asyncio
async def test_direct_delete_product_integrity_error(
    db_session: AsyncSession,
    admin_user: User,
    regular_user: User,
) -> None:
    """Direct invocation of delete_product raising 409 on IntegrityError."""
    product = Product(
        name="Direct Conflict",
        price=Decimal("5.00"),
        category=CategoryType.COFFEE,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    order = Order(
        user_id=regular_user.id,
        status=OrderStatus.PENDING,
        total_amount=Decimal("5.00"),
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=Decimal("5.00"),
    )
    db_session.add(item)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await delete_product(id=product.id, _=admin_user, db=db_session)
    assert exc_info.value.status_code == 409
    assert "associated orders" in exc_info.value.detail
