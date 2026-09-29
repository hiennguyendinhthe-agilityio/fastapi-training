"""
tests/repositories/test_product_repo.py
Unit & Integration tests for app/repositories/product_repo.py.

Tests cover:
- get_by_id (found and not found)
- get_all (empty DB, pagination slicing, category filtering, safe boundary defaults)
- create (persisting new products with server-generated audit fields)
- update (partial field updates, explicit null updates, preserving unset fields)
- delete (removing records from DB)
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import CategoryType, Product
from app.repositories import product_repo
from app.schemas.product import ProductCreateRequest, ProductUpdateRequest


@pytest.mark.asyncio
async def test_get_by_id_found(db_session: AsyncSession) -> None:
    """get_by_id returns the matching Product when ID exists."""
    product = Product(
        name="Mocha Deluxe",
        description="Espresso with chocolate and cream",
        price=Decimal("4.50"),
        category=CategoryType.COFFEE,
        is_available=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    found = await product_repo.get_by_id(db_session, product.id)
    assert found is not None
    assert found.id == product.id
    assert found.name == "Mocha Deluxe"
    assert found.price == Decimal("4.50")
    assert found.category == CategoryType.COFFEE


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: AsyncSession) -> None:
    """get_by_id returns None for a random UUID."""
    random_id = uuid.uuid4()
    found = await product_repo.get_by_id(db_session, random_id)
    assert found is None


@pytest.mark.asyncio
async def test_create_product(db_session: AsyncSession) -> None:
    """create persists a product and returns hydrated ORM object."""
    req = ProductCreateRequest(
        name="Butter Croissant",
        description="Fresh French pastry",
        price=Decimal("3.25"),
        category=CategoryType.PASTRY,
        image_url="https://images.unsplash.com/croissant.jpg",
        is_available=True,
    )

    created = await product_repo.create(db_session, req)

    assert created.id is not None
    assert created.name == "Butter Croissant"
    assert created.price == Decimal("3.25")
    assert created.category == CategoryType.PASTRY
    assert created.image_url == "https://images.unsplash.com/croissant.jpg"
    assert created.is_available is True
    assert created.created_at is not None
    assert created.updated_at is not None

    # Verify queryable from DB
    persisted = await product_repo.get_by_id(db_session, created.id)
    assert persisted is not None
    assert persisted.name == "Butter Croissant"


@pytest.mark.asyncio
async def test_update_product_partial(db_session: AsyncSession) -> None:
    """update applies only provided fields and leaves omitted fields unchanged."""
    product = Product(
        name="Cold Brew Original",
        description="Slow steeped for 18 hours",
        price=Decimal("4.00"),
        category=CategoryType.COFFEE,
        is_available=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    update_dto = ProductUpdateRequest(
        price=Decimal("4.75"),
        is_available=False,
    )
    updated = await product_repo.update(db_session, product, update_dto)

    assert updated.price == Decimal("4.75")
    assert updated.is_available is False
    # Unset fields remain unchanged
    assert updated.name == "Cold Brew Original"
    assert updated.description == "Slow steeped for 18 hours"
    assert updated.category == CategoryType.COFFEE


@pytest.mark.asyncio
async def test_update_product_explicit_null(db_session: AsyncSession) -> None:
    """update can clear nullable fields when explicitly passed as None."""
    product = Product(
        name="Matcha Latte",
        description="Ceremonial grade matcha",
        price=Decimal("5.00"),
        category=CategoryType.SEASONAL,
        image_url="https://images.unsplash.com/matcha.jpg",
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    update_dto = ProductUpdateRequest(
        description=None,
        image_url=None,
    )
    # Note: in Pydantic, passing None explicitly will set them in
    # model_dump(exclude_unset=True) when constructed with kwargs
    updated = await product_repo.update(db_session, product, update_dto)
    assert updated.description is None
    assert updated.image_url is None
    assert updated.name == "Matcha Latte"


@pytest.mark.asyncio
async def test_delete_product(db_session: AsyncSession) -> None:
    """delete removes the product from the database."""
    product = Product(
        name="Temporary Scone",
        price=Decimal("2.50"),
        category=CategoryType.PASTRY,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    product_id = product.id

    await product_repo.delete(db_session, product)

    found = await product_repo.get_by_id(db_session, product_id)
    assert found is None


@pytest.mark.asyncio
async def test_get_all_empty_db(db_session: AsyncSession) -> None:
    """get_all returns empty PageResponse when no products exist."""
    res = await product_repo.get_all(db_session, page=1, size=10)
    assert res.total == 0
    assert res.items == []
    assert res.page == 1
    assert res.size == 10
    assert res.pages == 0


@pytest.mark.asyncio
async def test_get_all_pagination_slicing(db_session: AsyncSession) -> None:
    """get_all calculates pagination windows and total count accurately."""
    products = [
        Product(
            name=f"Coffee #{i}",
            price=Decimal("3.00"),
            category=CategoryType.COFFEE,
        )
        for i in range(5)
    ]
    db_session.add_all(products)
    await db_session.commit()

    page1 = await product_repo.get_all(db_session, page=1, size=2)
    assert page1.total == 5
    assert len(page1.items) == 2
    assert page1.page == 1
    assert page1.size == 2
    assert page1.pages == 3

    page2 = await product_repo.get_all(db_session, page=2, size=2)
    assert len(page2.items) == 2
    assert page2.page == 2

    page3 = await product_repo.get_all(db_session, page=3, size=2)
    assert len(page3.items) == 1
    assert page3.page == 3


@pytest.mark.asyncio
async def test_get_all_category_filtering(db_session: AsyncSession) -> None:
    """get_all filters both count and items when category is specified."""
    db_session.add_all(
        [
            Product(
                name="Espresso", price=Decimal("2.50"), category=CategoryType.COFFEE
            ),
            Product(name="Latte", price=Decimal("4.00"), category=CategoryType.COFFEE),
            Product(name="Danish", price=Decimal("3.50"), category=CategoryType.PASTRY),
            Product(
                name="Family Bundle",
                price=Decimal("15.00"),
                category=CategoryType.BUNDLE,
            ),
        ]
    )
    await db_session.commit()

    coffee_page = await product_repo.get_all(
        db_session, page=1, size=10, category=CategoryType.COFFEE
    )
    assert coffee_page.total == 2
    assert len(coffee_page.items) == 2
    assert all(item.category == CategoryType.COFFEE for item in coffee_page.items)

    pastry_page = await product_repo.get_all(
        db_session, page=1, size=10, category=CategoryType.PASTRY
    )
    assert pastry_page.total == 1
    assert pastry_page.items[0].name == "Danish"

    seasonal_page = await product_repo.get_all(
        db_session, page=1, size=10, category=CategoryType.SEASONAL
    )
    assert seasonal_page.total == 0
    assert seasonal_page.items == []


@pytest.mark.asyncio
async def test_get_all_safe_boundary_defaults(db_session: AsyncSession) -> None:
    """get_all guards against 0 or negative page/size values."""
    db_session.add(
        Product(name="Flat White", price=Decimal("3.75"), category=CategoryType.COFFEE)
    )
    await db_session.commit()

    res = await product_repo.get_all(db_session, page=-1, size=-5)
    assert res.total == 1
    assert len(res.items) == 1
