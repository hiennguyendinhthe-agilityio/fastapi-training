"""
tests/test_database.py
Tests for database engine, get_db dependency, lifespan, and health check endpoint.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db as deps_get_db
from app.core.database import get_db, normalize_database_url
from app.main import app, lifespan
from tests.conftest import TestingSessionLocal, test_engine


def test_normalize_database_url():
    """Verify postgresql:// URLs are normalized to postgresql+asyncpg://."""
    raw_url = "postgresql://user:password@localhost:5432/test_db"
    assert (
        normalize_database_url(raw_url)
        == "postgresql+asyncpg://user:password@localhost:5432/test_db"
    )

    already_async = "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert normalize_database_url(already_async) == already_async

    sqlite_url = "sqlite+aiosqlite:///:memory:"
    assert normalize_database_url(sqlite_url) == sqlite_url


def test_deps_reexports_get_db():
    """Verify app.api.deps re-exports get_db correctly."""
    assert deps_get_db is get_db


async def test_test_engine_connection():
    """Verify test engine can establish a connection and execute SELECT 1."""
    async with test_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


async def test_get_db_yields_active_session():
    """Verify get_db dependency yields a valid, usable AsyncSession."""
    with patch("app.core.database.AsyncSessionLocal", TestingSessionLocal):
        db_gen = get_db()
        session = await anext(db_gen)
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        with pytest.raises(StopAsyncIteration):
            await anext(db_gen)


async def test_get_db_rollback_on_exception():
    """Verify get_db calls rollback and propagates exceptions when errors occur."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    class MockSessionContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    with patch(
        "app.core.database.AsyncSessionLocal", return_value=MockSessionContext()
    ):
        db_gen = get_db()
        session = await anext(db_gen)
        assert session == mock_session

        with pytest.raises(RuntimeError, match="Simulated database failure"):
            await db_gen.athrow(RuntimeError("Simulated database failure"))

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()


async def test_app_lifespan_success():
    """Verify app lifespan successfully pings the database and disposes pool."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    class MockConnectContext:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    mock_engine.connect.return_value = MockConnectContext()
    mock_engine.dispose = AsyncMock()

    with patch("app.main.async_engine", mock_engine):
        async with lifespan(app):
            mock_conn.execute.assert_awaited_once()
        mock_engine.dispose.assert_awaited_once()


async def test_app_lifespan_db_failure():
    """Verify app lifespan catches database connection errors gracefully."""
    mock_engine = MagicMock()

    class FailingConnectContext:
        async def __aenter__(self):
            raise ConnectionError("Database unreachable")

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    mock_engine.connect.return_value = FailingConnectContext()
    mock_engine.dispose = AsyncMock()

    with patch("app.main.async_engine", mock_engine):
        async with lifespan(app):
            pass
        mock_engine.dispose.assert_awaited_once()


async def test_health_check_endpoint(client: AsyncClient):
    """Verify GET /health returns 200 and expected service status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "cocoloco-api"
