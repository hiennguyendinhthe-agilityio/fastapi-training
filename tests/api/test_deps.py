"""
tests/api/test_deps.py
Unit tests for app/api/deps.py dependency injection functions.

Test matrix:
- get_current_user:
  [1] Happy path: valid token + active USER → returns User
  [2] Happy path: valid token + active ADMIN → returns User
  [3] Missing Authorization header → 401
  [4] Invalid/expired token → 401 (delegates to verify_clerk_token)
  [5] Valid token but clerk_id not found in DB → 404
  [6] Valid token but user.is_active=False → 403 (Soft-Disable Active Guard)
- require_admin:
  [7] Current user has ADMIN role → returns user (pass-through)
  [8] Current user has USER role → 403
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.models.user import User, UserRole

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(
    *,
    role: UserRole = UserRole.USER,
    is_active: bool = True,
    clerk_id: str = "clerk_test_123",
) -> User:
    """Helper to create a minimal User ORM instance (not persisted)."""
    return User(
        id=uuid.uuid4(),
        clerk_id=clerk_id,
        email=f"{clerk_id}@test.com",
        full_name="Test User",
        role=role,
        is_active=is_active,
    )


def _make_credentials(token: str = "valid.jwt.token") -> HTTPAuthorizationCredentials:
    """Create an HTTPAuthorizationCredentials mock with a Bearer scheme."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def mock_db() -> AsyncMock:
    """Return a mock AsyncSession with chainable execute().scalar_one_or_none()."""
    session = AsyncMock(spec=AsyncSession)
    return session


def _mock_db_returning(session: AsyncMock, user: User | None) -> None:
    """
    Configure the mock db session to return `user` on scalar_one_or_none().

    db.execute() is awaited → AsyncMock.
    result.scalar_one_or_none() is NOT awaited (sync SQLAlchemy Result) → MagicMock.
    """
    mock_result = MagicMock()  # sync, not a coroutine
    mock_result.scalar_one_or_none.return_value = user
    session.execute = AsyncMock(return_value=mock_result)


# ---------------------------------------------------------------------------
# get_current_user tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_happy_path_user_role(mock_db: AsyncMock) -> None:
    """[1] Valid token + active USER → returns User with correct clerk_id."""
    fake_user = _make_user(role=UserRole.USER, is_active=True)
    _mock_db_returning(mock_db, fake_user)

    with patch(
        "app.api.deps.verify_clerk_token",
        return_value={"sub": fake_user.clerk_id},
    ):
        result = await get_current_user(
            credentials=_make_credentials(),
            db=mock_db,
        )

    assert result is fake_user
    assert result.role == UserRole.USER
    assert result.is_active is True


@pytest.mark.asyncio
async def test_get_current_user_happy_path_admin_role(mock_db: AsyncMock) -> None:
    """[2] Valid token + active ADMIN → returns User with ADMIN role."""
    fake_admin = _make_user(
        role=UserRole.ADMIN, is_active=True, clerk_id="clerk_admin_001"
    )
    _mock_db_returning(mock_db, fake_admin)

    with patch(
        "app.api.deps.verify_clerk_token",
        return_value={"sub": fake_admin.clerk_id},
    ):
        result = await get_current_user(
            credentials=_make_credentials("admin.jwt.token"),
            db=mock_db,
        )

    assert result is fake_admin
    assert result.role == UserRole.ADMIN
    assert result.is_admin is True


@pytest.mark.asyncio
async def test_get_current_user_missing_header(mock_db: AsyncMock) -> None:
    """[3] Missing Authorization header (credentials=None) → HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None, db=mock_db)

    assert exc_info.value.status_code == 401
    assert "Missing Authorization header" in exc_info.value.detail
    # WWW-Authenticate header must be present per RFC 9110
    assert exc_info.value.headers is not None
    assert "WWW-Authenticate" in exc_info.value.headers


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_db: AsyncMock) -> None:
    """[4] verify_clerk_token raises 401 → propagated directly to caller."""
    with patch(
        "app.api.deps.verify_clerk_token",
        side_effect=HTTPException(status_code=401, detail="Invalid token"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=_make_credentials("bad.token.here"),
                db=mock_db,
            )

    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_clerk_id_not_in_db(mock_db: AsyncMock) -> None:
    """[5] Valid JWT but clerk_id has no matching User in DB → HTTP 404."""
    _mock_db_returning(mock_db, None)  # DB returns no user

    with patch(
        "app.api.deps.verify_clerk_token",
        return_value={"sub": "clerk_nonexistent_999"},
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=_make_credentials(),
                db=mock_db,
            )

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()
    assert "/auth/sync" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_deactivated_account(mock_db: AsyncMock) -> None:
    """[6] Valid token but user.is_active=False → HTTP 403 (Soft-Disable Guard)."""
    disabled_user = _make_user(is_active=False)
    _mock_db_returning(mock_db, disabled_user)

    with patch(
        "app.api.deps.verify_clerk_token",
        return_value={"sub": disabled_user.clerk_id},
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=_make_credentials(),
                db=mock_db,
            )

    assert exc_info.value.status_code == 403
    assert "deactivated" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# require_admin tests
# ---------------------------------------------------------------------------


def test_require_admin_with_admin_user() -> None:
    """[7] ADMIN role → returns the user unchanged (pass-through guard)."""
    admin_user = _make_user(role=UserRole.ADMIN)
    result = require_admin(current_user=admin_user)
    assert result is admin_user


def test_require_admin_with_regular_user() -> None:
    """[8] USER role → HTTP 403 Forbidden."""
    regular_user = _make_user(role=UserRole.USER)
    with pytest.raises(HTTPException) as exc_info:
        require_admin(current_user=regular_user)

    assert exc_info.value.status_code == 403
    assert "Admin privileges required" in exc_info.value.detail
