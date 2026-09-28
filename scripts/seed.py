"""Seed script for Cocoloco database.

Populates initial menu items (coffee, pastries, bundles, seasonal items).
Idempotent: updates existing items by name or inserts missing ones.
"""

import asyncio
import logging
import sys
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import AsyncSessionLocal, async_engine
from app.models.product import CategoryType, Product

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

INITIAL_PRODUCTS = [
    {
        "name": "Cappuccino",
        "description": (
            "Rich espresso topped with velvety steamed milk foam and artisanal dusting."
        ),
        "price": Decimal("3.00"),
        "category": CategoryType.COFFEE,
        "image_url": "https://images.unsplash.com/photo-1572442388796-11668a67e53d",
        "is_available": True,
    },
    {
        "name": "Croissant",
        "description": (
            "Golden, flaky French pastry baked fresh daily with pure cultured butter."
        ),
        "price": Decimal("3.00"),
        "category": CategoryType.PASTRY,
        "image_url": "https://images.unsplash.com/photo-1555507036-ab1f4038808a",
        "is_available": True,
    },
    {
        "name": "Breakfast Bundle",
        "description": (
            "Morning combo: hot Cappuccino + Butter Croissant + fresh seasonal side."
        ),
        "price": Decimal("12.00"),
        "category": CategoryType.BUNDLE,
        "image_url": "https://images.unsplash.com/photo-1533089860892-a7c6f0a88666",
        "is_available": True,
    },
    {
        "name": "Latte Art Pour",
        "description": (
            "Signature single-origin espresso with silky handcrafted microfoam rosette."
        ),
        "price": Decimal("4.00"),
        "category": CategoryType.COFFEE,
        "image_url": "https://images.unsplash.com/photo-1534778101976-62847782c213",
        "is_available": True,
    },
    {
        "name": "Fresh Pasta",
        "description": (
            "Handmade seasonal tagliatelle with fresh Genovese basil and aged parmesan."
        ),
        "price": Decimal("8.00"),
        "category": CategoryType.SEASONAL,
        "image_url": "https://images.unsplash.com/photo-1551183053-bf91a1d81141",
        "is_available": True,
    },
    {
        "name": "Fruit Market Bowl",
        "description": (
            "Vibrant medley of organic seasonal fruits with Greek yogurt and honey."
        ),
        "price": Decimal("6.00"),
        "category": CategoryType.SEASONAL,
        "image_url": "https://images.unsplash.com/photo-1511690656952-34342bb7c2f2",
        "is_available": True,
    },
]


async def seed_products(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> int:
    """Seed or update initial Cocoloco products in an idempotent manner."""
    logger.info("🌱 Starting database seeding for Cocoloco products...")
    seeded_count = 0
    factory = session_factory or AsyncSessionLocal

    async with factory() as session:
        async with session.begin():
            for item in INITIAL_PRODUCTS:
                result = await session.execute(
                    select(Product).where(Product.name == item["name"])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Update fields to match seed data
                    existing.description = item["description"]
                    existing.price = item["price"]
                    existing.category = item["category"]
                    existing.image_url = item["image_url"]
                    existing.is_available = item["is_available"]
                    logger.info(
                        "🔄 Updated existing product: %s ($%s) [%s]",
                        existing.name,
                        existing.price,
                        existing.category.value,
                    )
                else:
                    new_product = Product(
                        name=item["name"],
                        description=item["description"],
                        price=item["price"],
                        category=item["category"],
                        image_url=item["image_url"],
                        is_available=item["is_available"],
                    )
                    session.add(new_product)
                    logger.info(
                        "✨ Created new product: %s ($%s) [%s]",
                        new_product.name,
                        new_product.price,
                        new_product.category.value,
                    )
                seeded_count += 1

        # Query all products to verify current database state
        all_products_res = await session.execute(
            select(Product).order_by(Product.category, Product.name)
        )
        products = all_products_res.scalars().all()

        logger.info("\n📊 --- Current Cocoloco Menu (%d items) ---", len(products))
        for p in products:
            logger.info(
                "  • [%-8s] %-20s : $%6.2f | Available: %s (ID: %s)",
                p.category.value,
                p.name,
                p.price,
                p.is_available,
                p.id,
            )

    return seeded_count


async def main() -> None:
    try:
        await seed_products()
        logger.info("🎉 Database seeding completed successfully!")
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
