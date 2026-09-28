"""
tests/test_product_model.py
Unit tests for Product model and CategoryType enum.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import CategoryType, Product


def test_category_type_enum():
    """Verify CategoryType enum values match API contract and Flutter tabs."""
    assert CategoryType.COFFEE.value == "coffee"
    assert CategoryType.PASTRY.value == "pastry"
    assert CategoryType.BUNDLE.value == "bundle"
    assert CategoryType.SEASONAL.value == "seasonal"


def test_product_model_defaults_and_repr():
    """Verify default field values and informative __repr__ format."""
    product = Product(
        name="Cappuccino",
        price=Decimal("3.00"),
        category=CategoryType.COFFEE,
    )
    assert isinstance(product.id, UUID)
    assert product.name == "Cappuccino"
    assert product.price == Decimal("3.00")
    assert product.category == CategoryType.COFFEE
    assert product.description is None
    assert product.image_url is None
    assert product.is_available is True

    product_repr = repr(product)
    assert "Product" in product_repr
    assert "name='Cappuccino'" in product_repr
    assert "category=<CategoryType.COFFEE: 'coffee'>" in product_repr


async def test_create_and_query_products(db_session: AsyncSession):
    """Verify persisting products across categories and query filtering."""
    cappuccino = Product(
        name="Cappuccino",
        description="Rich espresso with steamed milk foam",
        price=Decimal("3.00"),
        image_url="https://cocoloco.io/images/cappuccino.jpg",
        category=CategoryType.COFFEE,
    )
    croissant = Product(
        name="Croissant",
        description="Buttery French pastry",
        price=Decimal("3.00"),
        category=CategoryType.PASTRY,
    )
    bundle = Product(
        name="Breakfast Bundle",
        description="Coffee and croissant combo",
        price=Decimal("12.00"),
        category=CategoryType.BUNDLE,
        is_available=False,
    )

    db_session.add_all([cappuccino, croissant, bundle])
    await db_session.commit()
    await db_session.refresh(cappuccino)

    assert cappuccino.created_at is not None
    assert cappuccino.updated_at is not None
    assert cappuccino.price == Decimal("3.00")

    # Filter by category: coffee
    coffee_stmt = select(Product).where(Product.category == CategoryType.COFFEE)
    coffee_result = await db_session.execute(coffee_stmt)
    coffee_items = coffee_result.scalars().all()
    assert len(coffee_items) == 1
    assert coffee_items[0].name == "Cappuccino"

    # Filter by availability: only available items
    available_stmt = select(Product).where(Product.is_available.is_(True))
    available_result = await db_session.execute(available_stmt)
    available_items = available_result.scalars().all()
    assert len(available_items) == 2
    assert all(item.is_available for item in available_items)


async def test_update_and_delete_product(db_session: AsyncSession):
    """Verify updating fields and deleting a Product entity."""
    product = Product(
        name="Fresh Pasta",
        price=Decimal("8.00"),
        category=CategoryType.SEASONAL,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Update price and description
    product.price = Decimal("8.50")
    product.description = "Handmade artisan pasta"
    await db_session.commit()
    await db_session.refresh(product)

    assert product.price == Decimal("8.50")
    assert product.description == "Handmade artisan pasta"

    # Delete product
    await db_session.delete(product)
    await db_session.commit()

    deleted_stmt = select(Product).where(Product.id == product.id)
    deleted_result = await db_session.execute(deleted_stmt)
    assert deleted_result.scalar_one_or_none() is None
