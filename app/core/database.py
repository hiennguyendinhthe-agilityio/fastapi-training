"""
app/core/database.py
Async SQLAlchemy engine, AsyncSessionLocal sessionmaker, and get_db dependency.

All database I/O is asynchronous using the asyncpg driver (PostgreSQL)
or aiosqlite driver (in-memory SQLite for testing).
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()


def normalize_database_url(url: str) -> str:
    """Ensure postgresql+asyncpg driver prefix is used for PostgreSQL connections."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL: str = normalize_database_url(
    os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://cocoloco:cocoloco123@localhost:5433/cocoloco_db",
    )
)

# Connection pool configuration:
# pool_size and max_overflow are supported by QueuePool (used for PostgreSQL),
# but NOT by StaticPool / NullPool (used for SQLite in-memory tests).
engine_kwargs: dict[str, object] = {
    "echo": False,
    "pool_pre_ping": True,
}

if not DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
        }
    )

async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    **engine_kwargs,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI async dependency yielding an isolated AsyncSession per request.

    Guarantees:
    - Dedicated session per HTTP request.
    - Automatic rollback on any unhandled exception.
    - Clean session closing and connection release back to pool.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
