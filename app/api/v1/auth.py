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
from app.schemas.user import UserResponse

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
) -> User:
    """
    Upsert the authenticated user into the local database.

    **When to call:** Immediately after the user signs in or signs up via Clerk
    in the Flutter app. Safe to call multiple times — idempotent operation.

    **What it does:**
    - Decodes the Bearer JWT (via `get_current_user` dependency).
    - Inserts a new User row if this is the first login (`clerk_id` not found).
    - Updates `email` and `full_name` on subsequent calls to keep the local record
      in sync with any Clerk profile changes.

    **What it does NOT do:**
    - It never changes a user's `role`. Role promotion to ADMIN is a separate
      admin-only operation.
    - It never deactivates a user. Deactivation is an admin-only operation.

    **Returns:** The full `UserResponse` reflecting the current DB state.
    """
    # current_user is already verified (token valid, account active) by the dependency.
    # We call upsert to refresh email/full_name from whatever was in the JWT claims —
    # the dependency already fetched the user but we re-upsert to sync any profile
    # changes from Clerk that may have occurred since last login.
    updated_user = await user_repo.upsert(
        db,
        clerk_id=current_user.clerk_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
    )
    return updated_user
