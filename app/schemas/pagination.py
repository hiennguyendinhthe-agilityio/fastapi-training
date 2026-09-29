"""
app/schemas/pagination.py
Generic Pydantic schema for paginated responses.

Provides:
- PageResponse[T]: A generic model for returning paginated lists of items.
  Supports metadata like total items, current page, size, and total pages.
"""

from collections.abc import Sequence
from math import ceil

from pydantic import BaseModel, ConfigDict, Field


class PageResponse[T](BaseModel):
    """
    Generic paginated response wrapper.
    Used for endpoints that return lists of resources (users, products, orders).
    """

    model_config = ConfigDict(from_attributes=True)

    items: Sequence[T] = Field(description="The list of items on the current page")
    total: int = Field(description="Total number of items across all pages")
    page: int = Field(description="Current page number (1-indexed)")
    size: int = Field(description="Number of items requested per page")
    pages: int = Field(description="Total number of pages available")

    @classmethod
    def create(
        cls, items: Sequence[T], total: int, page: int, size: int
    ) -> "PageResponse[T]":
        """
        Helper to construct a PageResponse, calculating the total pages automatically.
        """
        # Protect against division by zero if size is somehow 0
        safe_size = size if size > 0 else 1
        pages = ceil(total / safe_size)
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
