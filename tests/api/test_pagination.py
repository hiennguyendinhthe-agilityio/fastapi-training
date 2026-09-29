"""
tests/api/test_pagination.py
Unit tests for the generic PageResponse[T] Pydantic model.
"""

from pydantic import BaseModel

from app.schemas.pagination import PageResponse


class SimpleItem(BaseModel):
    id: int
    name: str


def test_page_response_create() -> None:
    """Test the create classmethod calculates pages correctly."""
    items = [SimpleItem(id=1, name="Item 1"), SimpleItem(id=2, name="Item 2")]

    # Total 5 items, size 2 -> 3 pages
    page = PageResponse[SimpleItem].create(items=items, total=5, page=1, size=2)

    assert page.items == items
    assert page.total == 5
    assert page.page == 1
    assert page.size == 2
    assert page.pages == 3


def test_page_response_create_exact_division() -> None:
    """Test the create classmethod when total is exactly divisible by size."""
    items = [SimpleItem(id=1, name="Item 1"), SimpleItem(id=2, name="Item 2")]

    # Total 4 items, size 2 -> 2 pages
    page = PageResponse[SimpleItem].create(items=items, total=4, page=1, size=2)

    assert page.pages == 2


def test_page_response_create_zero_size() -> None:
    """Test that size 0 does not cause division by zero."""
    items = [SimpleItem(id=1, name="Item 1")]

    page = PageResponse[SimpleItem].create(items=items, total=1, page=1, size=0)

    assert page.size == 0
    assert page.pages == 1  # Fallback to size 1 logic internally for division
