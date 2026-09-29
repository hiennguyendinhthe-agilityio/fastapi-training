"""
tests/api/test_users.py
Integration tests for User API endpoints:
- GET /api/v1/users/me
- PUT /api/v1/users/me
- GET /api/v1/users
- PATCH /api/v1/users/{id}/status
"""

import uuid
from typing import Any

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.api.v1.users import set_user_status, update_my_profile
from app.main import app
from app.models.user import User, UserRole
from app.schemas.user import UserStatusRequest, UserUpdateRequest


def _override_user(user: User) -> Any:
    """Return a dependency override callable that returns the given user."""

    async def _inner() -> User:
        return user

    return _inner


# ---------------------------------------------------------------------------
# GET /api/v1/users/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_my_profile_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /users/me returns authenticated user's profile."""
    user = User(
        clerk_id=f"clerk_me_{uuid.uuid4().hex[:8]}",
        email="me@cocoloco.com",
        full_name="Me Tester",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    app.dependency_overrides[get_current_user] = _override_user(user)
    try:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email"] == "me@cocoloco.com"
        assert data["full_name"] == "Me Tester"
        assert data["role"] == UserRole.USER
        assert data["is_active"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_get_my_profile_missing_token(client: AsyncClient) -> None:
    """GET /users/me without token returns 401."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/v1/users/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_my_profile_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """PUT /users/me updates full_name and returns 200."""
    user = User(
        clerk_id=f"clerk_upd_{uuid.uuid4().hex[:8]}",
        email="update@cocoloco.com",
        full_name="Old Name",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    app.dependency_overrides[get_current_user] = _override_user(user)
    try:
        response = await client.put(
            "/api/v1/users/me",
            json={"full_name": "New Full Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Full Name"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_update_my_profile_empty_body(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """PUT /users/me with empty body leaves full_name unchanged."""
    user = User(
        clerk_id=f"clerk_upd_empty_{uuid.uuid4().hex[:8]}",
        email="empty_upd@cocoloco.com",
        full_name="Keep This Name",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    app.dependency_overrides[get_current_user] = _override_user(user)
    try:
        response = await client.put("/api/v1/users/me", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Keep This Name"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_update_my_profile_empty_string_fails(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """PUT /users/me with empty string violates min_length=1 -> 422."""
    user = User(
        clerk_id=f"clerk_empty_str_{uuid.uuid4().hex[:8]}",
        email="empty_str@cocoloco.com",
        full_name="Valid Name",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = _override_user(user)
    try:
        response = await client.put("/api/v1/users/me", json={"full_name": ""})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


# ---------------------------------------------------------------------------
# GET /api/v1/users (Admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_users_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /users as admin returns paginated users."""
    admin = User(
        clerk_id=f"clerk_admin_{uuid.uuid4().hex[:8]}",
        email="admin@cocoloco.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    app.dependency_overrides[require_admin] = _override_user(admin)
    try:
        response = await client.get("/api/v1/users?page=1&size=5")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert data["page"] == 1
        assert data["size"] == 5
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_list_users_as_regular_user_forbidden(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /users as regular user returns 403 Forbidden."""
    regular_user = User(
        clerk_id=f"clerk_reg_{uuid.uuid4().hex[:8]}",
        email="reg@cocoloco.com",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(regular_user)
    await db_session.commit()

    # Real require_admin checks role != ADMIN and raises 403
    app.dependency_overrides[get_current_user] = _override_user(regular_user)
    try:
        response = await client.get("/api/v1/users")
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_list_users_invalid_pagination_query(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /users with page=0 or size=0 violates ge=1 -> 422."""
    admin = User(
        clerk_id=f"clerk_admin_query_{uuid.uuid4().hex[:8]}",
        email="admin_query@cocoloco.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    app.dependency_overrides[require_admin] = _override_user(admin)
    try:
        response = await client.get("/api/v1/users?page=0&size=10")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


# ---------------------------------------------------------------------------
# PATCH /api/v1/users/{id}/status (Admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_user_status_deactivate(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Admin deactivates another user -> 200, is_active=False."""
    admin = User(
        id=uuid.uuid4(),
        clerk_id=f"clerk_admin_stat_{uuid.uuid4().hex[:8]}",
        email="admin_stat@cocoloco.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    target_user = User(
        id=uuid.uuid4(),
        clerk_id=f"clerk_target_{uuid.uuid4().hex[:8]}",
        email="target@cocoloco.com",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add_all([admin, target_user])
    await db_session.commit()

    app.dependency_overrides[require_admin] = _override_user(admin)
    try:
        response = await client.patch(
            f"/api/v1/users/{target_user.id}/status",
            json={"is_active": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(target_user.id)
        assert data["is_active"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_set_user_status_admin_cannot_disable_self(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Admin Self-Lock Guard: admin cannot disable themselves -> 403."""
    admin_id = uuid.uuid4()
    admin = User(
        id=admin_id,
        clerk_id=f"clerk_self_lock_{uuid.uuid4().hex[:8]}",
        email="self_lock@cocoloco.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    app.dependency_overrides[require_admin] = _override_user(admin)
    try:
        response = await client.patch(
            f"/api/v1/users/{admin_id}/status",
            json={"is_active": False},
        )
        assert response.status_code == 403
        assert "Admin cannot disable themselves" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_set_user_status_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Admin toggles status for unknown user ID -> 404."""
    admin = User(
        id=uuid.uuid4(),
        clerk_id=f"clerk_admin_nf_{uuid.uuid4().hex[:8]}",
        email="admin_nf@cocoloco.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    random_id = uuid.uuid4()
    app.dependency_overrides[require_admin] = _override_user(admin)
    try:
        response = await client.patch(
            f"/api/v1/users/{random_id}/status",
            json={"is_active": True},
        )
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_direct_update_my_profile(db_session: AsyncSession) -> None:
    """Direct invocation of update_my_profile router handler."""
    user = User(
        clerk_id=f"clerk_dir_{uuid.uuid4().hex[:8]}",
        email="direct@cocoloco.com",
        full_name="Original Name",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    updated = await update_my_profile(
        current_user=user,
        payload=UserUpdateRequest(full_name="Directly Updated"),
        db=db_session,
    )
    assert updated.full_name == "Directly Updated"


@pytest.mark.asyncio
async def test_direct_set_user_status(db_session: AsyncSession) -> None:
    """Direct invocation of set_user_status router handler."""
    admin = User(
        id=uuid.uuid4(),
        clerk_id=f"clerk_dir_adm_{uuid.uuid4().hex[:8]}",
        email="dir_adm@cocoloco.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    target = User(
        id=uuid.uuid4(),
        clerk_id=f"clerk_dir_tgt_{uuid.uuid4().hex[:8]}",
        email="dir_tgt@cocoloco.com",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add_all([admin, target])
    await db_session.commit()

    # Success: Admin toggles target user status
    res = await set_user_status(
        id=target.id,
        payload=UserStatusRequest(is_active=False),
        admin=admin,
        db=db_session,
    )
    assert res.is_active is False

    # Failure: Target user not found -> 404
    with pytest.raises(HTTPException) as exc_info:
        await set_user_status(
            id=uuid.uuid4(),
            payload=UserStatusRequest(is_active=True),
            admin=admin,
            db=db_session,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"
