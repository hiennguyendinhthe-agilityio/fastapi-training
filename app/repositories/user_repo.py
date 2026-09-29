"""
app/repositories/user_repo.py
Data access layer for User entity — async repository pattern.

Implemented progressively:
- Task 3.5: get_by_clerk_id(), upsert() — required by POST /auth/sync.
- Task 4.2: get_by_id(), update(), set_status(), get_all() — required by Users API.

All methods accept an AsyncSession injected via FastAPI's Depends(get_db).
No raw SQL is exposed to callers; all DB exceptions are handled at the router layer.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


async def get_by_clerk_id(db: AsyncSession, clerk_id: str) -> User | None:
    """
    Fetch a User record by Clerk subject identifier (clerk_id = JWT sub claim).

    Returns None if no matching record exists — caller decides how to respond.
    Used by: POST /auth/sync, GET /users/me (via get_current_user dependency).
    """
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    return result.scalar_one_or_none()


async def upsert(
    db: AsyncSession,
    *,
    clerk_id: str,
    email: str,
    full_name: str | None = None,
    role: UserRole = UserRole.USER,
) -> User:
    """
    Insert or update a User record keyed by clerk_id.

    - If the clerk_id already exists: updates email and full_name (if provided).
    - If not found: creates a new User with UserRole.USER by default.

    The role field is intentionally NOT updated on subsequent calls — role
    changes are admin-only operations (PATCH /users/{id}/status pathway).

    Commits the transaction and refreshes the instance before returning so the
    caller always receives a fully hydrated ORM object with server-generated
    values (id, created_at, updated_at).

    Used by: POST /api/v1/auth/sync
    """
    user = await get_by_clerk_id(db, clerk_id)

    if user is None:
        # First login — create a new User record
        user = User(
            clerk_id=clerk_id,
            email=email,
            full_name=full_name,
            role=role,
        )
        db.add(user)
    else:
        # Subsequent login — sync email and full_name from Clerk token claims
        user.email = email
        if full_name is not None:
            user.full_name = full_name

    await db.commit()
    # Re-fetch by clerk_id to guarantee fresh data from DB (bypass identity map cache).
    # This is necessary because AsyncSessionLocal sets expire_on_commit=False.
    refreshed = await get_by_clerk_id(db, clerk_id)
    if refreshed is None:  # pragma: no cover
        raise RuntimeError(
            f"upsert commit succeeded but clerk_id={clerk_id!r} not found"
        )
    return refreshed
