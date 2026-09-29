"""
app/api/v1/products.py
Product endpoints: catalog browsing and admin product management.

Implemented in: Task 5.3

Endpoints:
- GET /products: Browse products with pagination and optional category filtering.
- GET /products/{id}: Get detailed information for a single product by UUID.
- POST /products: Admin-only creation of a new product item.
- PUT /products/{id}: Admin-only partial or full update of an existing product.
- DELETE /products/{id}: Admin-only permanent deletion of a product.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models.product import CategoryType, Product
from app.models.user import User
from app.repositories import product_repo
from app.schemas.pagination import PageResponse
from app.schemas.product import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "",
    response_model=PageResponse[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="Browse products catalog",
    response_description="A paginated list of catalog products",
)
async def list_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    category: CategoryType | None = Query(
        default=None,
        description="Optional filter by category (coffee, pastry, bundle, seasonal)",
    ),
) -> PageResponse[ProductResponse]:
    """
    Retrieve a paginated list of products from the catalog.

    Supports optional category filtering matching the mobile app navigation tabs.
    Public endpoint: accessible without authentication.
    """
    return await product_repo.get_all(db, page=page, size=size, category=category)


@router.get(
    "/{id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product details",
    response_description="Detailed product record",
)
async def get_product(
    id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    """
    Retrieve single product details by primary key UUID.

    Public endpoint: accessible without authentication.
    """
    product = await product_repo.get_by_id(db, id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product (Admin only)",
    response_description="The newly created product record",
)
async def create_product(
    payload: ProductCreateRequest,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    """
    Add a new product item to the store catalog.

    **RBAC:** Restricted to ADMIN role only. Non-admin users receive 403 Forbidden.
    """
    return await product_repo.create(db, payload)


@router.put(
    "/{id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Update product details (Admin only)",
    response_description="The updated product record",
)
async def update_product(
    id: uuid.UUID,
    payload: ProductUpdateRequest,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    """
    Update attributes of an existing product item.

    Supports partial updates via exclude_unset.
    **RBAC:** Restricted to ADMIN role only. Non-admin users receive 403 Forbidden.
    """
    product = await product_repo.get_by_id(db, id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return await product_repo.update(db, product, payload)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product (Admin only)",
    response_description="Product successfully deleted",
)
async def delete_product(
    id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Permanently remove a product item from the store catalog.

    **RBAC:** Restricted to ADMIN role only. Non-admin users receive 403 Forbidden.
    """
    product = await product_repo.get_by_id(db, id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    await product_repo.delete(db, product)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
