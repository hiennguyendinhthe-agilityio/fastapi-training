"""
tests/test_base_model.py
Unit tests for Base and TimestampedBase declarative models.
"""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class SampleEntity(TimestampedBase):
    """Concrete model for testing TimestampedBase functionality."""

    __tablename__ = "test_sample_entities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


async def test_base_model_repr():
    """Verify __repr__ formats loaded attributes cleanly."""
    entity = SampleEntity(id=1, name="Coffee Bean")
    repr_str = repr(entity)
    assert "SampleEntity" in repr_str
    assert "id=1" in repr_str
    assert "name='Coffee Bean'" in repr_str


async def test_timestamped_base_timestamps(db_session: AsyncSession):
    """Verify created_at and updated_at are automatically populated."""
    entity = SampleEntity(name="Latte")
    db_session.add(entity)
    await db_session.commit()
    await db_session.refresh(entity)

    assert entity.id is not None
    assert entity.name == "Latte"
    assert isinstance(entity.created_at, datetime)
    assert isinstance(entity.updated_at, datetime)


async def test_timestamped_base_update(db_session: AsyncSession):
    """Verify updated record retains valid timestamps."""
    entity = SampleEntity(name="Espresso")
    db_session.add(entity)
    await db_session.commit()
    await db_session.refresh(entity)

    initial_created_at = entity.created_at

    entity.name = "Double Espresso"
    await db_session.commit()
    await db_session.refresh(entity)

    # created_at must remain unchanged
    assert entity.created_at == initial_created_at
    assert entity.name == "Double Espresso"
