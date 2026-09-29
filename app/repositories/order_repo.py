"""
app/repositories/order_repo.py
Data access layer for Order and OrderItem entities — async repository pattern.

Implemented in: Task 6.2

Provides:
- ProductNotFoundError, ProductUnavailableError: Domain exceptions.
- create(db, user_id, items) -> Order: Validates products, snapshots unit prices,
  calculates total server-side, and commits atomically.
- get_by_id(db, order_id) -> Order | None: Eagerly loads items and product relations.
- get_by_user(db, user_id, page, size) -> PageResponse[OrderResponse]:
  Paginated user order history.
- get_all(db, page, size) -> PageResponse[OrderResponse]:
  Paginated listing for store admins.
- update_status(db, order, status) -> Order: Updates order lifecycle status.

All methods accept an AsyncSession injected via FastAPI's Depends(get_db).
No raw SQL is exposed to callers; all database exceptions are handled
at the router layer.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.schemas.order import OrderItemInput, OrderResponse
from app.schemas.pagination import PageResponse


class ProductNotFoundError(Exception):
    """Raised during order creation when an ordered product UUID does not exist."""

    def __init__(self, product_id: uuid.UUID) -> None:
        super().__init__(f"Product with id '{product_id}' not found.")
        self.product_id = product_id


class ProductUnavailableError(Exception):
    """Raised during order creation when an ordered product is marked unavailable."""

    def __init__(self, product_name: str, product_id: uuid.UUID) -> None:
        super().__init__(
            f"Product '{product_name}' ({product_id}) is unavailable."
        )
        self.product_name = product_name
        self.product_id = product_id


async def get_by_id(db: AsyncSession, order_id: uuid.UUID) -> Order | None:
    """
    Fetch an Order record by primary key (id: UUID) with all associated
    OrderItem records and their referenced Product records eagerly loaded.

    Uses `selectinload(Order.items).joinedload(OrderItem.product)` to eliminate
    N+1 queries and guarantee safe access to `OrderItem.product_name` and
    `OrderItem.subtotal` without triggering `MissingGreenlet` in async execution.

    Returns None if no order exists with the specified UUID.
    Used by: GET /api/v1/orders/{id}, PATCH /api/v1/orders/{id}/status.
    """
    stmt = (
        select(Order)
        .options(selectinload(Order.items).joinedload(OrderItem.product))
        .where(Order.id == order_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    items: list[OrderItemInput],
) -> Order:
    """
    Atomically create a new Order and its line items (OrderItems).

    Enforces Price Sovereignty & Business Rules:
    1. Zero Client-Side Price Trust: Query the database for current product prices.
    2. Availability Verification: Ordered products must have `is_available == True`.
    3. Price Snapshotting: Copies current `product.price` to `order_item.unit_price`.
    4. Server-Side Arithmetic: `total_amount = sum(quantity * unit_price)`.
    5. Atomic Commit: All records are inserted in a single transaction.

    Raises:
        ProductNotFoundError: If any product_id cannot be found in the catalog.
        ProductUnavailableError: If any product is disabled / out of stock.

    Returns:
        The newly created Order ORM object with its items and products fully hydrated.
    """
    product_ids = [item.product_id for item in items]

    # Fetch all relevant products in a single batch query
    stmt = select(Product).where(Product.id.in_(product_ids))
    result = await db.execute(stmt)
    products = result.scalars().all()
    product_map: dict[uuid.UUID, Product] = {p.id: p for p in products}

    # Validate existence and availability in memory
    total_amount = Decimal("0.00")
    order_items: list[OrderItem] = []
    order_id = uuid.uuid4()

    for item_input in items:
        product = product_map.get(item_input.product_id)
        if product is None:
            raise ProductNotFoundError(product_id=item_input.product_id)

        if not product.is_available:
            raise ProductUnavailableError(
                product_name=product.name,
                product_id=product.id,
            )

        snapshotted_price = product.price
        line_subtotal = snapshotted_price * Decimal(item_input.quantity)
        total_amount += line_subtotal

        order_item = OrderItem(
            order_id=order_id,
            product_id=product.id,
            quantity=item_input.quantity,
            unit_price=snapshotted_price,
        )
        order_items.append(order_item)

    # Instantiate and persist the order
    order = Order(
        id=order_id,
        user_id=user_id,
        status=OrderStatus.PENDING,
        total_amount=total_amount,
        items=order_items,
    )

    db.add(order)
    await db.commit()

    # Re-fetch with eager loading so caller receives fully hydrated entity
    hydrated = await get_by_id(db, order_id)
    assert hydrated is not None, "Order must exist immediately after commit"
    return hydrated


async def get_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    page: int = 1,
    size: int = 10,
) -> PageResponse[OrderResponse]:
    """
    Fetch a paginated list of orders placed by a specific user.
    Ordered by `ordered_at` descending (most recent first).

    Executes two queries:
    1. SELECT count(id) WHERE user_id = :user_id for total pagination count.
    2. SELECT with offset, limit, and eager loading for the current page window.

    Returns:
        PageResponse[OrderResponse] DTO.
    Used by: GET /api/v1/orders/me.
    """
    safe_page = page if page > 0 else 1
    safe_size = size if size > 0 else 10
    offset = (safe_page - 1) * safe_size

    # 1. Total count query
    count_stmt = select(func.count(Order.id)).where(Order.user_id == user_id)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # 2. Window query with eager loading
    stmt = (
        select(Order)
        .options(selectinload(Order.items).joinedload(OrderItem.product))
        .where(Order.user_id == user_id)
        .order_by(Order.ordered_at.desc())
        .offset(offset)
        .limit(safe_size)
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()

    items = [OrderResponse.model_validate(o) for o in orders]
    return PageResponse[OrderResponse].create(
        items=items,
        total=total,
        page=page,
        size=size,
    )


async def get_all(
    db: AsyncSession,
    *,
    page: int = 1,
    size: int = 10,
) -> PageResponse[OrderResponse]:
    """
    Fetch a paginated list of all orders across the entire platform.
    Ordered by `ordered_at` descending (most recent first).

    Executes two queries:
    1. SELECT count(id) to compute total count.
    2. SELECT with offset, limit, and eager loading for the current page window.

    Returns:
        PageResponse[OrderResponse] DTO.
    Used by: GET /api/v1/orders (Admin-only).
    """
    safe_page = page if page > 0 else 1
    safe_size = size if size > 0 else 10
    offset = (safe_page - 1) * safe_size

    # 1. Total count query
    count_stmt = select(func.count(Order.id))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # 2. Window query with eager loading
    stmt = (
        select(Order)
        .options(selectinload(Order.items).joinedload(OrderItem.product))
        .order_by(Order.ordered_at.desc())
        .offset(offset)
        .limit(safe_size)
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()

    items = [OrderResponse.model_validate(o) for o in orders]
    return PageResponse[OrderResponse].create(
        items=items,
        total=total,
        page=page,
        size=size,
    )


async def update_status(
    db: AsyncSession,
    order: Order,
    status: OrderStatus,
) -> Order:
    """
    Update an order's lifecycle status (e.g. PENDING -> CONFIRMED -> COMPLETED).

    Commits the transaction and re-loads the full relation graph so the caller
    receives a consistent hydrated object.

    Used by: PATCH /api/v1/orders/{id}/status (Admin-only).
    """
    order.status = status
    await db.commit()

    reloaded = await get_by_id(db, order.id)
    assert reloaded is not None, "Order must exist immediately after commit"
    return reloaded
