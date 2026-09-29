"""
app/schemas/product.py
Pydantic v2 Data Transfer Objects (DTOs) for the Product entity.

Enforces schema contracts for:
- ProductResponse: Public representation of a menu product with exact Decimal price.
- ProductCreateRequest: Admin payload to create a new product catalog item.
- ProductUpdateRequest: Admin payload to partially or fully update an existing product.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.product import CategoryType


class ProductResponse(BaseModel):
    """
    Public representation of a Product returned by API endpoints.

    Fields align with the Product ORM model. `model_config` enables automatic
    conversion from SQLAlchemy ORM instances (from_attributes=True).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID v4) of the product",
    )
    name: str = Field(
        ...,
        description="Display name of the product",
        examples=["Cappuccino"],
    )
    description: str | None = Field(
        default=None,
        description="Detailed description of the product and its ingredients",
        examples=[
            "Rich espresso topped with velvety steamed milk foam and artisanal dusting."
        ],
    )
    price: Decimal = Field(
        ...,
        description="Unit price in USD with 2 decimal places",
        examples=[Decimal("3.00")],
    )
    image_url: str | None = Field(
        default=None,
        description="Public URL to the product image asset",
        examples=["https://images.unsplash.com/photo-1572442388796-11668a67e53d"],
    )
    category: CategoryType = Field(
        ...,
        description="Product catalog category matching Flutter menu tabs",
        examples=[CategoryType.COFFEE],
    )
    is_available: bool = Field(
        ...,
        description="Availability status (true if item can be ordered)",
        examples=[True],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when product was created",
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp when product was last updated",
    )


class ProductCreateRequest(BaseModel):
    """
    Request body for creating a new product (Admin only).
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name of the product",
        examples=["Cappuccino"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Detailed description of the product and its ingredients",
        examples=[
            "Rich espresso topped with velvety steamed milk foam and artisanal dusting."
        ],
    )
    price: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Unit price in USD (must be positive, max 2 decimal places)",
        examples=[Decimal("3.00")],
    )
    image_url: str | None = Field(
        default=None,
        max_length=1024,
        description="Web URL to product image asset",
        examples=["https://images.unsplash.com/photo-1572442388796-11668a67e53d"],
    )
    category: CategoryType = Field(
        ...,
        description="Product catalog category (coffee, pastry, bundle, seasonal)",
        examples=[CategoryType.COFFEE],
    )
    is_available: bool = Field(
        default=True,
        description=(
            "Whether the product is currently active and available for ordering"
        ),
        examples=[True],
    )

    @field_validator("name", mode="after")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Product name cannot be empty or whitespace only")
        return cleaned

    @field_validator("image_url", mode="after")
    @classmethod
    def validate_image_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return None
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            raise ValueError("Image URL must start with http:// or https://")
        return cleaned


class ProductUpdateRequest(BaseModel):
    """
    Request body for updating an existing product (Admin only).
    All fields are optional. Only provided fields will be updated.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated display name of the product",
        examples=["Iced Cappuccino"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Updated description of the product",
        examples=["Double espresso over ice with silky microfoam."],
    )
    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description=(
            "Updated unit price in USD (must be positive, max 2 decimal places)"
        ),
        examples=[Decimal("3.50")],
    )
    image_url: str | None = Field(
        default=None,
        max_length=1024,
        description="Updated web URL of the product image",
        examples=["https://images.unsplash.com/photo-1572442388796-11668a67e53d"],
    )
    category: CategoryType | None = Field(
        default=None,
        description="Updated product category",
        examples=[CategoryType.COFFEE],
    )
    is_available: bool | None = Field(
        default=None,
        description="Updated availability flag",
        examples=[False],
    )

    @field_validator("name", mode="after")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Product name cannot be empty or whitespace only")
        return cleaned

    @field_validator("image_url", mode="after")
    @classmethod
    def validate_image_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return None
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            raise ValueError("Image URL must start with http:// or https://")
        return cleaned
