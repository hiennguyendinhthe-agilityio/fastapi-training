"""
app/api/v1/auth.py
Authentication router — POST /api/v1/auth/sync.

Implemented in: Task 3.5

Endpoint:
- POST /auth/sync: Called by the Flutter app immediately after Clerk login.
  Upserts the authenticated user into the local PostgreSQL database so the API
  can associate orders, roles, and other data to a local User record.

Design decision:
- This is an authenticated endpoint (requires a valid Clerk JWT), which prevents
  anonymous users from creating accounts without going through Clerk's login flow.
- The `sub` claim provides the stable clerk_id; `email` and `name` claims from
  the JWT payload are used to populate / refresh the local record.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories import user_repo
from app.schemas.user import AuthSyncRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/sync",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync authenticated Clerk user to local database",
    response_description="The upserted user record",
)
async def sync_user(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    sync_data: AuthSyncRequest | None = None,
) -> User:
    """
    Upsert the authenticated user into the local database.

    **When to call:** Immediately after the user signs in or signs up via Clerk
    in the Flutter app. Safe to call multiple times — idempotent operation.

    **What it does:**
    - Decodes the Bearer JWT (via `get_current_user` dependency).
    - Inserts a new User row if this is the first login (`clerk_id` not found).
    - Updates `email`, `full_name`, and `avatar_url` from sync_data (if provided)
      or JWT token claims to keep the local record in sync.

    **What it does NOT do:**
    - It never changes a user's `role`. Role promotion to ADMIN is a separate
      admin-only operation.
    - It never deactivates a user. Deactivation is an admin-only operation.

    **Returns:** The full `UserResponse` reflecting the current DB state.
    """
    email = sync_data.email if sync_data and sync_data.email else current_user.email
    full_name = (
        sync_data.full_name
        if sync_data and sync_data.full_name is not None
        else current_user.full_name
    )
    avatar_url = (
        sync_data.avatar_url
        if sync_data and sync_data.avatar_url is not None
        else getattr(current_user, "avatar_url", None)
    )

    updated_user = await user_repo.upsert(
        db,
        clerk_id=current_user.clerk_id,
        email=email,
        full_name=full_name,
        role=current_user.role,
        avatar_url=avatar_url,
    )
    return updated_user
