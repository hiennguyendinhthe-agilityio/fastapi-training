"""
app/repositories/user_repo.py
Data access layer for User entity — async repository pattern.

Implemented in:
- Task 3.5: get_by_clerk_id(), upsert() — required by POST /auth/sync.
- Task 4.2: get_by_id(), update(), set_status(), get_all() — required by Users API.

All methods accept an AsyncSession injected via FastAPI's Depends(get_db).
No raw SQL is exposed to callers; all DB exceptions are handled at the router layer.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.schemas.pagination import PageResponse
from app.schemas.user import UserResponse, UserUpdateRequest


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """
    Fetch a User record by primary key (id: UUID).

    Returns None if no matching record exists — caller decides how to
    respond (e.g. 404).
    Used by: PATCH /users/{id}/status (Admin-only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


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


async def update(db: AsyncSession, user: User, data: UserUpdateRequest) -> User:
    """
    Apply partial profile updates to an existing User instance.

    Currently updates full_name if provided in the DTO.
    Commits the transaction and refreshes the instance before returning.
    Used by: PUT /api/v1/users/me.
    """
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


async def set_status(db: AsyncSession, user: User, is_active: bool) -> User:
    """
    Update the active status of a user (soft-disable or re-enable).

    Used by: PATCH /api/v1/users/{id}/status (Admin-only).
    Commits the transaction and refreshes the instance before returning.
    """
    user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    return user


async def get_all(
    db: AsyncSession,
    *,
    page: int = 1,
    size: int = 10,
) -> PageResponse[UserResponse]:
    """
    Fetch a paginated list of all users, ordered by created_at descending.

    Executes two queries:
    1. SELECT count(id) to compute total items across all pages.
    2. SELECT with offset and limit to fetch the current page items.

    Returns a PageResponse[UserResponse] DTO.
    Used by: GET /api/v1/users (Admin-only).
    """
    safe_page = page if page > 0 else 1
    safe_size = size if size > 0 else 10
    offset = (safe_page - 1) * safe_size

    # Total count query across the entire users table
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar_one()

    # Query the current page with pagination window
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(safe_size)
    result = await db.execute(stmt)
    users = result.scalars().all()

    items = [UserResponse.model_validate(u) for u in users]
    return PageResponse[UserResponse].create(
        items=items,
        total=total,
        page=page,
        size=size,
    )
