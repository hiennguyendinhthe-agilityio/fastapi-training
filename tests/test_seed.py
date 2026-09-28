"""tests/test_seed.py
Unit tests for Cocoloco database seeding script.

Verifies:
- Complete insertion of initial Cocoloco products into isolated test database.
- Idempotency: running seed multiple times does not create duplicates.
- Correct precision and category mappings.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.product import CategoryType, Product
from scripts.seed import INITIAL_PRODUCTS, seed_products
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_seed_products_inserts_all_items() -> None:
    """Verify seed_products inserts all initial items into the database."""
    count = await seed_products(session_factory=TestingSessionLocal)
    assert count == len(INITIAL_PRODUCTS)
    assert count == 6

    async with TestingSessionLocal() as session:
        result = await session.execute(select(Product))
        products = result.scalars().all()
        assert len(products) == 6

        # Check required specific products
        product_map = {p.name: p for p in products}

        assert "Cappuccino" in product_map
        assert product_map["Cappuccino"].price == Decimal("3.00")
        assert product_map["Cappuccino"].category == CategoryType.COFFEE

        assert "Croissant" in product_map
        assert product_map["Croissant"].price == Decimal("3.00")
        assert product_map["Croissant"].category == CategoryType.PASTRY

        assert "Breakfast Bundle" in product_map
        assert product_map["Breakfast Bundle"].price == Decimal("12.00")
        assert product_map["Breakfast Bundle"].category == CategoryType.BUNDLE

        assert "Latte Art Pour" in product_map
        assert product_map["Latte Art Pour"].price == Decimal("4.00")
        assert product_map["Latte Art Pour"].category == CategoryType.COFFEE

        assert "Fresh Pasta" in product_map
        assert product_map["Fresh Pasta"].price == Decimal("8.00")
        assert product_map["Fresh Pasta"].category == CategoryType.SEASONAL

        assert "Fruit Market Bowl" in product_map
        assert product_map["Fruit Market Bowl"].price == Decimal("6.00")
        assert product_map["Fruit Market Bowl"].category == CategoryType.SEASONAL


@pytest.mark.asyncio
async def test_seed_products_idempotency() -> None:
    """Verify executing seed_products twice updates records without duplicates."""
    first_count = await seed_products(session_factory=TestingSessionLocal)
    assert first_count == 6

    # Run a second time
    second_count = await seed_products(session_factory=TestingSessionLocal)
    assert second_count == 6

    async with TestingSessionLocal() as session:
        result = await session.execute(select(Product))
        products = result.scalars().all()
        # Still exactly 6 products, no duplicates created
        assert len(products) == 6
