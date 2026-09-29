"""
app/repositories/product_repo.py
Data access layer for the Product entity — async repository pattern.

Implemented in: Task 5.2

Provides:
- get_by_id(db, product_id) -> Product | None
- get_all(db, page, size, category) -> PageResponse[ProductResponse]
- create(db, data) -> Product
- update(db, product, data) -> Product
- delete(db, product) -> None

All methods accept an AsyncSession injected via FastAPI's Depends(get_db).
No raw SQL is exposed to callers; all database exceptions are handled
at the router layer.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import CategoryType, Product
from app.schemas.pagination import PageResponse
from app.schemas.product import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)


async def get_by_id(db: AsyncSession, product_id: uuid.UUID) -> Product | None:
    """
    Fetch a Product record by primary key (id: UUID).

    Returns None if no matching product exists.
    Used by: GET /api/v1/products/{id}, PUT /api/v1/products/{id},
    DELETE /api/v1/products/{id}.
    """
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all(
    db: AsyncSession,
    *,
    page: int = 1,
    size: int = 10,
    category: CategoryType | None = None,
) -> PageResponse[ProductResponse]:
    """
    Fetch a paginated list of products, optionally filtered by catalog category.
    Ordered by created_at descending.

    Executes two queries:
    1. SELECT count(id) with optional category filter to compute total items.
    2. SELECT with offset and limit to fetch the current page items.

    Returns a PageResponse[ProductResponse] DTO.
    Used by: GET /api/v1/products (public catalog).
    """
    safe_page = page if page > 0 else 1
    safe_size = size if size > 0 else 10
    offset = (safe_page - 1) * safe_size

    # 1. Total count query
    count_stmt = select(func.count(Product.id))
    if category is not None:
        count_stmt = count_stmt.where(Product.category == category)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # 2. Window query
    stmt = select(Product)
    if category is not None:
        stmt = stmt.where(Product.category == category)
    stmt = stmt.order_by(Product.created_at.desc()).offset(offset).limit(safe_size)
    result = await db.execute(stmt)
    products = result.scalars().all()

    items = [ProductResponse.model_validate(p) for p in products]
    return PageResponse[ProductResponse].create(
        items=items,
        total=total,
        page=page,
        size=size,
    )


async def create(db: AsyncSession, data: ProductCreateRequest) -> Product:
    """
    Insert a new Product record into the database.

    Commits the transaction and refreshes the instance before returning so the
    caller always receives a fully hydrated ORM object with server-generated
    values (id, created_at, updated_at).

    Used by: POST /api/v1/products (Admin-only).
    """
    product = Product(
        name=data.name,
        description=data.description,
        price=data.price,
        image_url=data.image_url,
        category=data.category,
        is_available=data.is_available,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update(
    db: AsyncSession,
    product: Product,
    data: ProductUpdateRequest,
) -> Product:
    """
    Apply partial or full updates to an existing Product instance.

    Uses exclude_unset=True to ensure only fields explicitly provided by the
    caller are updated, preserving existing values for omitted fields.

    Commits the transaction and refreshes the instance before returning.
    Used by: PUT /api/v1/products/{id} (Admin-only).
    """
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


async def delete(db: AsyncSession, product: Product) -> None:
    """
    Permanently delete a Product record from the database.

    Used by: DELETE /api/v1/products/{id} (Admin-only).
    """
    await db.delete(product)
    await db.commit()
