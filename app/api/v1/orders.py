"""
app/api/v1/orders.py
Order endpoints: checkout, history tracking, detail lookup, and admin lifecycle updates.

Implemented in: Task 6.3

Endpoints:
- POST /orders: Place a new food & coffee order (Customer).
- GET /orders/me: Paginated personal order history (Customer).
- GET /orders/{id}: View order details (Owner or Admin).
- GET /orders: Paginated list of all platform orders (Admin only).
- PATCH /orders/{id}/status: Update order lifecycle status (Admin only).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_admin
from app.models.user import User, UserRole
from app.repositories import order_repo
from app.schemas.order import (
    OrderCreateRequest,
    OrderResponse,
    OrderStatusRequest,
)
from app.schemas.pagination import PageResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
    response_description="The placed order with snapshotted pricing",
)
async def create_order(
    payload: OrderCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrderResponse:
    """
    Place a new food & coffee order.

    Security & Validation:
    - Enforces authentication via Clerk JWT and checks account is active.
    - Product prices are NEVER taken from the client payload. Prices are read
      directly from the database and snapshotted onto each line item.
    - Rejects the checkout if any item is not found (404) or marked unavailable (400).
    - Calculates total_amount server-side to guarantee financial integrity.
    """
    try:
        order = await order_repo.create(
            db,
            user_id=current_user.id,
            items=payload.items,
        )
    except order_repo.ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except order_repo.ProductUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return OrderResponse.model_validate(order)


@router.get(
    "/me",
    response_model=PageResponse[OrderResponse],
    status_code=status.HTTP_200_OK,
    summary="Get personal order history",
    response_description="A paginated list of orders placed by the current user",
)
async def list_my_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
) -> PageResponse[OrderResponse]:
    """
    Retrieve paginated order history for the authenticated user.
    Sorted by ordered_at descending (most recent first).
    """
    return await order_repo.get_by_user(
        db,
        user_id=current_user.id,
        page=page,
        size=size,
    )


@router.get(
    "/{id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get order details",
    response_description="Detailed order info including line items and status",
)
async def get_order_by_id(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrderResponse:
    """
    Fetch a single order by its UUID.

    Access Control:
    - Regular users can only access their own orders (403 Forbidden otherwise).
    - Admins can access any order across the platform.
    """
    order = await order_repo.get_by_id(db, id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id '{id}' not found.",
        )

    if current_user.role != UserRole.ADMIN and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this order.",
        )

    return OrderResponse.model_validate(order)


@router.get(
    "",
    response_model=PageResponse[OrderResponse],
    status_code=status.HTTP_200_OK,
    summary="List all platform orders (Admin only)",
    response_description="Paginated list of all orders across all users",
)
async def list_all_orders(
    _admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
) -> PageResponse[OrderResponse]:
    """
    Admin-only endpoint to view all customer orders across the platform.
    Sorted by ordered_at descending.
    """
    return await order_repo.get_all(db, page=page, size=size)


@router.patch(
    "/{id}/status",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update order lifecycle status (Admin only)",
    response_description="The order with updated status",
)
async def update_order_status(
    id: uuid.UUID,
    payload: OrderStatusRequest,
    _admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrderResponse:
    """
    Admin-only endpoint to update an order's status (CONFIRMED, COMPLETED, CANCELLED).
    """
    order = await order_repo.get_by_id(db, id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id '{id}' not found.",
        )

    updated = await order_repo.update_status(db, order, payload.status)
    return OrderResponse.model_validate(updated)
