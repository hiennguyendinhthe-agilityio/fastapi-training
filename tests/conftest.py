"""
tests/conftest.py
Pytest async configuration and fixtures.

Provides:
- In-memory SQLite async engine with StaticPool (zero contamination of production DB).
- Database table creation & teardown per test.
- db_session fixture for direct session interaction.
- client fixture (httpx.AsyncClient) with get_db dependency override.
- fake_user, fake_admin fixtures.
- override_get_current_user helper for dependency injection.
- test_product, test_order shared fixtures.
"""

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.order import Order
from app.models.product import CategoryType, Product
from app.models.user import User, UserRole
from app.repositories import order_repo
from app.schemas.order import OrderItemInput

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def override_get_current_user(user: User) -> Any:
    """Helper to override get_current_user dependency with a specified User."""

    async def _inner() -> User:
        return user

    return _inner


@pytest.fixture(autouse=True)
async def prepare_database() -> AsyncGenerator[None, None]:
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an isolated test session for unit/integration tests."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield an AsyncClient for testing FastAPI endpoints with DB override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def fake_user(db_session: AsyncSession) -> User:
    """Create and return an active standard USER."""
    user = User(
        clerk_id=f"clerk_user_{uuid.uuid4().hex[:8]}",
        email=f"user_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Standard User",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def fake_admin(db_session: AsyncSession) -> User:
    """Create and return an active ADMIN user."""
    admin = User(
        clerk_id=f"clerk_admin_{uuid.uuid4().hex[:8]}",
        email=f"admin_{uuid.uuid4().hex[:6]}@cocoloco.com",
        full_name="Admin Chef",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def test_product(db_session: AsyncSession) -> Product:
    """Create and return an available sample product."""
    product = Product(
        name="Classic Espresso",
        description="Rich dark roast espresso",
        price=Decimal("3.50"),
        category=CategoryType.COFFEE,
        is_available=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_order(
    db_session: AsyncSession,
    fake_user: User,
    test_product: Product,
) -> Order:
    """Create and return a sample Order entity with items."""
    return await order_repo.create(
        db_session,
        user_id=fake_user.id,
        items=[OrderItemInput(product_id=test_product.id, quantity=2)],
    )
