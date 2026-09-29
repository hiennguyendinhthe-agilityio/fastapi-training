"""
tests/test_product_schemas.py
Comprehensive unit tests for Product Pydantic v2 schemas:
- ProductResponse
- ProductCreateRequest
- ProductUpdateRequest
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.product import CategoryType, Product
from app.schemas.product import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)


class TestProductResponse:
    """Tests for ProductResponse schema."""

    def test_product_response_valid(self) -> None:
        """Test ProductResponse instantiation with valid data."""
        now = datetime.now(UTC)
        product_id = uuid.uuid4()

        res = ProductResponse(
            id=product_id,
            name="Cappuccino",
            description="Artisanal espresso with steamed milk foam",
            price=Decimal("3.50"),
            image_url="https://images.unsplash.com/cappuccino.jpg",
            category=CategoryType.COFFEE,
            is_available=True,
            created_at=now,
            updated_at=now,
        )

        assert res.id == product_id
        assert res.name == "Cappuccino"
        assert res.price == Decimal("3.50")
        assert res.category == CategoryType.COFFEE
        assert res.is_available is True
        assert res.created_at == now

    def test_product_response_from_orm(self) -> None:
        """Test ProductResponse model_validate converts from SQLAlchemy ORM instance."""
        now = datetime.now(UTC)
        product = Product(
            name="Croissant",
            description="Flaky French pastry",
            price=Decimal("3.00"),
            category=CategoryType.PASTRY,
            image_url="https://images.unsplash.com/croissant.jpg",
            is_available=True,
        )
        # Mock audit timestamps that DB normally populates
        product.created_at = now
        product.updated_at = now

        res = ProductResponse.model_validate(product)

        assert res.id == product.id
        assert res.name == "Croissant"
        assert res.price == Decimal("3.00")
        assert res.category == CategoryType.PASTRY
        assert res.is_available is True
        assert res.created_at == now

    def test_product_response_missing_fields_fails(self) -> None:
        """Test that omitting required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductResponse(
                name="Cappuccino",  # missing id, price, category, etc.
            )  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        field_names = {err["loc"][0] for err in errors}
        assert "id" in field_names
        assert "price" in field_names
        assert "category" in field_names


class TestProductCreateRequest:
    """Tests for ProductCreateRequest schema."""

    def test_product_create_minimal_valid(self) -> None:
        """Test creating with only required fields (defaults for others)."""
        data = ProductCreateRequest(
            name="Americano",
            price=Decimal("2.50"),
            category=CategoryType.COFFEE,
        )

        assert data.name == "Americano"
        assert data.price == Decimal("2.50")
        assert data.category == CategoryType.COFFEE
        assert data.description is None
        assert data.image_url is None
        assert data.is_available is True

    def test_product_create_all_fields(self) -> None:
        """Test creating with all fields populated."""
        data = ProductCreateRequest(
            name="Breakfast Bundle",
            description="Coffee and croissant combo",
            price=Decimal("12.00"),
            image_url="https://images.unsplash.com/combo.jpg",
            category=CategoryType.BUNDLE,
            is_available=False,
        )

        assert data.name == "Breakfast Bundle"
        assert data.description == "Coffee and croissant combo"
        assert data.price == Decimal("12.00")
        assert data.category == CategoryType.BUNDLE
        assert data.image_url == "https://images.unsplash.com/combo.jpg"
        assert data.is_available is False

    def test_product_create_name_stripping(self) -> None:
        """Test that surrounding whitespace in name is stripped."""
        data = ProductCreateRequest(
            name="   Latte Art   ",
            price=Decimal("4.00"),
            category=CategoryType.COFFEE,
        )
        assert data.name == "Latte Art"

    def test_product_create_empty_name_fails(self) -> None:
        """Test that empty or whitespace-only name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductCreateRequest(
                name="    ",
                price=Decimal("4.00"),
                category=CategoryType.COFFEE,
            )
        assert "Product name cannot be empty" in str(exc_info.value)

    def test_product_create_price_from_float_and_str(self) -> None:
        """Test price coercion from float and string."""
        req1 = ProductCreateRequest.model_validate(
            {"name": "A", "price": 3.5, "category": CategoryType.COFFEE}
        )
        assert req1.price == Decimal("3.5")

        req2 = ProductCreateRequest.model_validate(
            {"name": "B", "price": "4.25", "category": CategoryType.COFFEE}
        )
        assert req2.price == Decimal("4.25")

    def test_product_create_zero_or_negative_price_fails(self) -> None:
        """Test that zero or negative prices are rejected."""
        with pytest.raises(ValidationError):
            ProductCreateRequest(
                name="Free Coffee",
                price=Decimal("0.00"),
                category=CategoryType.COFFEE,
            )

        with pytest.raises(ValidationError):
            ProductCreateRequest(
                name="Negative Coffee",
                price=Decimal("-2.00"),
                category=CategoryType.COFFEE,
            )

    def test_product_create_price_too_many_decimals_fails(self) -> None:
        """Test that more than 2 decimal places is rejected."""
        with pytest.raises(ValidationError):
            ProductCreateRequest(
                name="Micro-priced Coffee",
                price=Decimal("3.999"),
                category=CategoryType.COFFEE,
            )

    def test_product_create_invalid_category_fails(self) -> None:
        """Test that non-existent category raises ValidationError."""
        with pytest.raises(ValidationError):
            ProductCreateRequest(
                name="Burger",
                price=Decimal("5.00"),
                category="fastfood",  # type: ignore[arg-type]
            )

    def test_product_create_image_url_cleaning(self) -> None:
        """Test image_url stripping, empty string handling, and scheme validation."""
        # Strips whitespace
        req1 = ProductCreateRequest(
            name="Coffee",
            price=Decimal("3.00"),
            category=CategoryType.COFFEE,
            image_url="  https://images.unsplash.com/pic.jpg  ",
        )
        assert req1.image_url == "https://images.unsplash.com/pic.jpg"

        # Empty string becomes None
        req2 = ProductCreateRequest(
            name="Coffee",
            price=Decimal("3.00"),
            category=CategoryType.COFFEE,
            image_url="   ",
        )
        assert req2.image_url is None

        # Invalid scheme fails
        with pytest.raises(ValidationError) as exc_info:
            ProductCreateRequest(
                name="Coffee",
                price=Decimal("3.00"),
                category=CategoryType.COFFEE,
                image_url="ftp://example.com/pic.jpg",
            )
        assert "Image URL must start with http:// or https://" in str(exc_info.value)


class TestProductUpdateRequest:
    """Tests for ProductUpdateRequest schema."""

    def test_product_update_empty_valid(self) -> None:
        """Test that all fields are optional for partial updates."""
        req = ProductUpdateRequest()
        assert req.model_dump(exclude_unset=True) == {}

    def test_product_update_partial_fields(self) -> None:
        """Test partial update containing only a subset of fields."""
        req = ProductUpdateRequest(
            price=Decimal("4.50"),
            is_available=False,
        )
        dump = req.model_dump(exclude_unset=True)
        assert dump == {
            "price": Decimal("4.50"),
            "is_available": False,
        }

    def test_product_update_name_stripping_and_empty_check(self) -> None:
        """Test name validation on update."""
        req = ProductUpdateRequest(name="  Cold Brew  ")
        assert req.name == "Cold Brew"

        with pytest.raises(ValidationError) as exc_info:
            ProductUpdateRequest(name="   ")
        assert "Product name cannot be empty" in str(exc_info.value)

    def test_product_update_image_url_validation(self) -> None:
        """Test image_url validation on update."""
        req = ProductUpdateRequest(image_url="  http://cdn.example.com/new.png  ")
        assert req.image_url == "http://cdn.example.com/new.png"

        req_empty = ProductUpdateRequest(image_url="   ")
        assert req_empty.image_url is None

        with pytest.raises(ValidationError) as exc_info:
            ProductUpdateRequest(image_url="javascript:alert(1)")
        assert "Image URL must start with http:// or https://" in str(exc_info.value)

    def test_product_update_invalid_price(self) -> None:
        """Test invalid prices on update."""
        with pytest.raises(ValidationError):
            ProductUpdateRequest(price=Decimal("-1.00"))

        with pytest.raises(ValidationError):
            ProductUpdateRequest(price=Decimal("1.234"))

    def test_product_explicit_none_inputs(self) -> None:
        """Test explicit None inputs for optional fields."""
        create_req = ProductCreateRequest(
            name="Vanilla Latte",
            price=Decimal("4.50"),
            category=CategoryType.COFFEE,
            image_url=None,
        )
        assert create_req.image_url is None

        update_req = ProductUpdateRequest(
            name=None,
            image_url=None,
            price=None,
            category=None,
            is_available=None,
        )
        assert update_req.name is None
        assert update_req.image_url is None
