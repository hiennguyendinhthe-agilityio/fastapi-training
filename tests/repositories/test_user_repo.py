"""
tests/repositories/test_user_repo.py
Unit & Integration tests for app/repositories/user_repo.py.

Tests cover:
- get_by_id (found and not found)
- get_by_clerk_id (found and not found)
- upsert (insert new user and update existing user without changing role)
- update (apply UserUpdateRequest and handle unset fields)
- set_status (toggle is_active to False and back to True)
- get_all (pagination calculation, empty DB, multi-page slicing, safe boundary defaults)
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.repositories import user_repo
from app.schemas.user import UserUpdateRequest


@pytest.mark.asyncio
async def test_get_by_id_found(db_session: AsyncSession) -> None:
    """get_by_id returns the correct User when ID exists in DB."""
    user = User(
        clerk_id=f"clerk_id_test_{uuid.uuid4().hex[:8]}",
        email="id_test@cocoloco.com",
        full_name="ID Tester",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    found = await user_repo.get_by_id(db_session, user.id)
    assert found is not None
    assert found.id == user.id
    assert found.email == "id_test@cocoloco.com"
    assert found.clerk_id == user.clerk_id


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: AsyncSession) -> None:
    """get_by_id returns None for non-existent UUID."""
    random_id = uuid.uuid4()
    found = await user_repo.get_by_id(db_session, random_id)
    assert found is None


@pytest.mark.asyncio
async def test_get_by_clerk_id_found(db_session: AsyncSession) -> None:
    """get_by_clerk_id returns matching User when clerk_id exists."""
    clerk_id = f"clerk_sub_{uuid.uuid4().hex[:8]}"
    user = User(
        clerk_id=clerk_id,
        email="clerk_found@cocoloco.com",
        full_name="Clerk Found",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()

    found = await user_repo.get_by_clerk_id(db_session, clerk_id)
    assert found is not None
    assert found.clerk_id == clerk_id
    assert found.email == "clerk_found@cocoloco.com"


@pytest.mark.asyncio
async def test_get_by_clerk_id_not_found(db_session: AsyncSession) -> None:
    """get_by_clerk_id returns None for unknown clerk_id."""
    found = await user_repo.get_by_clerk_id(db_session, "non_existent_clerk_sub")
    assert found is None


@pytest.mark.asyncio
async def test_upsert_insert_and_update(db_session: AsyncSession) -> None:
    """upsert creates a new record on first call, updates profile on second call."""
    clerk_id = f"clerk_upsert_{uuid.uuid4().hex[:8]}"

    # 1. First call: INSERT
    user1 = await user_repo.upsert(
        db_session,
        clerk_id=clerk_id,
        email="initial@cocoloco.com",
        full_name="Initial Name",
        role=UserRole.ADMIN,
    )
    assert user1 is not None
    assert user1.clerk_id == clerk_id
    assert user1.email == "initial@cocoloco.com"
    assert user1.full_name == "Initial Name"
    assert user1.role == UserRole.ADMIN

    # 2. Second call: UPDATE (email and full_name refreshed, role preserved)
    user2 = await user_repo.upsert(
        db_session,
        clerk_id=clerk_id,
        email="changed@cocoloco.com",
        full_name="Changed Name",
        role=UserRole.USER,  # Attempt to pass USER role
    )
    assert user2.id == user1.id
    assert user2.email == "changed@cocoloco.com"
    assert user2.full_name == "Changed Name"
    # Role must still be ADMIN — protected against demotion
    assert user2.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_update_user_full_name(db_session: AsyncSession) -> None:
    """update applies full_name from UserUpdateRequest."""
    user = User(
        clerk_id=f"clerk_upd_{uuid.uuid4().hex[:8]}",
        email="update_me@cocoloco.com",
        full_name="Old Full Name",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    update_req = UserUpdateRequest(full_name="Brand New Name")
    updated = await user_repo.update(db_session, user, update_req)

    assert updated.full_name == "Brand New Name"

    # Verify directly from DB query
    refetched = await user_repo.get_by_id(db_session, user.id)
    assert refetched is not None
    assert refetched.full_name == "Brand New Name"


@pytest.mark.asyncio
async def test_update_user_noop_when_unset(db_session: AsyncSession) -> None:
    """update does not overwrite full_name when field is unset/None."""
    user = User(
        clerk_id=f"clerk_noop_{uuid.uuid4().hex[:8]}",
        email="noop@cocoloco.com",
        full_name="Preserve Me",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    update_req = UserUpdateRequest(full_name=None)
    updated = await user_repo.update(db_session, user, update_req)

    assert updated.full_name == "Preserve Me"


@pytest.mark.asyncio
async def test_set_status(db_session: AsyncSession) -> None:
    """set_status toggles user.is_active field and persists to DB."""
    user = User(
        clerk_id=f"clerk_status_{uuid.uuid4().hex[:8]}",
        email="status_toggle@cocoloco.com",
        full_name="Status Target",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Deactivate
    deactivated = await user_repo.set_status(db_session, user, is_active=False)
    assert deactivated.is_active is False

    # Re-enable
    activated = await user_repo.set_status(db_session, deactivated, is_active=True)
    assert activated.is_active is True


@pytest.mark.asyncio
async def test_get_all_empty_db(db_session: AsyncSession) -> None:
    """get_all on an empty DB returns 0 items and 0 pages."""
    # Note: SQLite in-memory DB per test function is clean
    res = await user_repo.get_all(db_session, page=1, size=10)
    assert res.items == []
    assert res.total == 0
    assert res.pages == 0
    assert res.page == 1
    assert res.size == 10


@pytest.mark.asyncio
async def test_get_all_pagination_slicing(db_session: AsyncSession) -> None:
    """get_all correctly slices records across multiple pages."""
    # Seed 5 users
    for i in range(5):
        u = User(
            clerk_id=f"clerk_page_{i}_{uuid.uuid4().hex[:6]}",
            email=f"page_user_{i}@cocoloco.com",
            full_name=f"User {i}",
            role=UserRole.USER,
        )
        db_session.add(u)
    await db_session.commit()

    # Page 1 (size 2) -> items 0, 1 of 5
    page1 = await user_repo.get_all(db_session, page=1, size=2)
    assert len(page1.items) == 2
    assert page1.total == 5
    assert page1.pages == 3
    assert page1.page == 1
    assert page1.size == 2

    # Page 2 (size 2) -> items 2, 3 of 5
    page2 = await user_repo.get_all(db_session, page=2, size=2)
    assert len(page2.items) == 2
    assert page2.page == 2

    # Page 3 (size 2) -> item 4 of 5 (1 item left)
    page3 = await user_repo.get_all(db_session, page=3, size=2)
    assert len(page3.items) == 1
    assert page3.page == 3

    # Ensure items on page 1 and page 2 are distinct
    p1_ids = {item.id for item in page1.items}
    p2_ids = {item.id for item in page2.items}
    assert p1_ids.isdisjoint(p2_ids)


@pytest.mark.asyncio
async def test_get_all_safe_boundary_values(db_session: AsyncSession) -> None:
    """get_all handles non-positive page and size safely without zero division."""
    user = User(
        clerk_id=f"clerk_boundary_{uuid.uuid4().hex[:6]}",
        email="boundary@cocoloco.com",
        full_name="Boundary User",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()

    # page=0, size=0
    res = await user_repo.get_all(db_session, page=0, size=0)
    assert res.total == 1
    assert len(res.items) == 1
    assert res.pages == 1
