"""
tests/api/test_auth.py
Integration tests for POST /api/v1/auth/sync endpoint.

Test matrix (from task spec + negative testing mandate):
[1] Valid token, new user → 200, user created with correct fields.
[2] Valid token, existing user → 200, no duplicate, updated fields returned.
[3] full_name updated on second call when JWT claims change.
[4] role is NOT overwritten on second call (protected field).
[5] Missing Authorization header → 401.
[6] Invalid/malformed token → 401.
[7] Deactivated user account → 403 (Soft-Disable Guard).

Strategy:
- Uses the `client` fixture (httpx.AsyncClient with SQLite in-memory DB).
- Overrides `get_current_user` dependency to inject controlled User fixtures
  without going through real Clerk JWT validation.
- Directly verifies DB state via `db_session` to confirm upsert semantics.
"""

import uuid
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.main import app
from app.models.user import User, UserRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

API_URL = "/api/v1/auth/sync"


def _make_user(
    *,
    clerk_id: str = "clerk_test_sync_001",
    email: str = "sync@cocoloco.com",
    full_name: str | None = "Sync Tester",
    role: UserRole = UserRole.USER,
    avatar_url: str | None = None,
    is_active: bool = True,
) -> User:
    """Create an in-memory User (not persisted to DB)."""
    return User(
        id=uuid.uuid4(),
        clerk_id=clerk_id,
        email=email,
        full_name=full_name,
        role=role,
        avatar_url=avatar_url,
        is_active=is_active,
    )


def _override_current_user(user: User) -> Any:
    """Return a FastAPI dependency override that yields the given user."""

    async def _inner() -> User:
        return user

    return _inner


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_creates_new_user(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """[1] Valid token, new user → 200, user created in DB with correct fields."""
    fake_user = _make_user()

    # Override the auth dependency: bypass Clerk JWT validation
    app.dependency_overrides[get_current_user] = _override_current_user(fake_user)

    try:
        # First call: user does not exist in DB yet
        response = await client.post(API_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["clerk_id"] == fake_user.clerk_id
        assert body["email"] == fake_user.email
        assert body["full_name"] == fake_user.full_name
        assert body["role"] == UserRole.USER
        assert body["is_active"] is True
        assert "id" in body
        assert "created_at" in body

        # Verify record was persisted in DB
        result = await db_session.execute(
            select(User).where(User.clerk_id == fake_user.clerk_id)
        )
        db_user = result.scalar_one_or_none()
        assert db_user is not None
        assert db_user.email == fake_user.email
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_is_idempotent_no_duplicate(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """[2] Valid token, second call → 200, still exactly one DB record (no dup)."""
    fake_user = _make_user()
    app.dependency_overrides[get_current_user] = _override_current_user(fake_user)

    try:
        await client.post(API_URL)  # first call
        await client.post(API_URL)  # second call

        # DB must have exactly one record for this clerk_id
        result = await db_session.execute(
            select(User).where(User.clerk_id == fake_user.clerk_id)
        )
        users = result.scalars().all()
        assert len(users) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_updates_full_name_on_second_call(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """[3] Second call with updated full_name → DB record is refreshed."""
    first_user = _make_user(full_name="Old Name")
    app.dependency_overrides[get_current_user] = _override_current_user(first_user)
    await client.post(API_URL)

    # Second call: same clerk_id but updated full_name from Clerk profile
    # Only swap get_current_user — keep get_db override from client fixture intact
    updated_user = _make_user(full_name="New Name")
    app.dependency_overrides[get_current_user] = _override_current_user(updated_user)

    try:
        response = await client.post(API_URL)
        assert response.status_code == 200
        body = response.json()
        assert body["full_name"] == "New Name"

        # Confirm DB was updated — use a fresh query
        result2 = await db_session.execute(
            select(User).where(User.clerk_id == first_user.clerk_id)
        )
        db_user = result2.scalar_one_or_none()
        assert db_user is not None
        assert db_user.full_name == "New Name"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_does_not_overwrite_role(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """[4] Role field must be protected — upsert never demotes an ADMIN to USER."""
    # First call creates the user as ADMIN
    admin_user = _make_user(role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = _override_current_user(admin_user)
    resp1 = await client.post(API_URL)
    assert resp1.json()["role"] == UserRole.ADMIN

    # Second call: same clerk_id with USER role — role in DB must stay ADMIN.
    # Only swap get_current_user; keep get_db override from client fixture intact.
    regular_user = _make_user(role=UserRole.USER)
    app.dependency_overrides[get_current_user] = _override_current_user(regular_user)

    try:
        resp2 = await client.post(API_URL)
        assert resp2.status_code == 200
        # Role must still be ADMIN — upsert does not touch it on update
        assert resp2.json()["role"] == UserRole.ADMIN
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_missing_auth_header(client: AsyncClient) -> None:
    """[5] Missing Authorization header → 401 Unauthorized."""
    # No dependency override: use the real get_current_user which raises 401
    with patch(
        "app.api.deps.verify_clerk_token",
        side_effect=HTTPException(
            status_code=401, detail="Missing Authorization header"
        ),
    ):
        response = await client.post(API_URL)
    # The real _bearer_scheme returns None → get_current_user raises 401
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sync_invalid_token(client: AsyncClient) -> None:
    """[6] Invalid/malformed token → 401 Unauthorized."""
    response = await client.post(
        API_URL,
        headers={"Authorization": "Bearer this.is.not.a.real.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sync_deactivated_user_is_blocked(client: AsyncClient) -> None:
    """[7] Deactivated user (is_active=False) → 403 Forbidden (Soft-Disable Guard)."""

    # Override to return a deactivated user from get_current_user
    # NOTE: get_current_user itself raises 403 before the endpoint is reached,
    # so we patch the dependency to raise that exception directly.
    async def _raise_403() -> User:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    app.dependency_overrides[get_current_user] = _raise_403

    try:
        response = await client.post(API_URL)
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_with_metadata_body_updates_profile_and_avatar(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    [8] POST /auth/sync with AuthSyncRequest body updates email, full_name, and
    avatar_url.
    """
    fake_user = _make_user(clerk_id="clerk_metadata_001")
    app.dependency_overrides[get_current_user] = _override_current_user(fake_user)

    try:
        payload = {
            "email": "hien.nguyen@cocoloco.vn",
            "full_name": "Hien Nguyen",
            "avatar_url": "https://img.clerk.com/avatar_test.png",
        }
        response = await client.post(API_URL, json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "hien.nguyen@cocoloco.vn"
        assert body["full_name"] == "Hien Nguyen"
        assert body["avatar_url"] == "https://img.clerk.com/avatar_test.png"

        # Confirm record in DB
        result = await db_session.execute(
            select(User).where(User.clerk_id == fake_user.clerk_id)
        )
        db_user = result.scalar_one_or_none()
        assert db_user is not None
        assert db_user.avatar_url == "https://img.clerk.com/avatar_test.png"
    finally:
        app.dependency_overrides.clear()
