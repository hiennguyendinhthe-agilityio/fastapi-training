"""
app/api/v1/users.py
User endpoints: /users/me, /users, and /users/{id}/status.

Implemented in: Task 4.3

Endpoints:
- GET /users/me: Return the authenticated user's profile.
- PUT /users/me: Update the authenticated user's full_name.
- GET /users: Admin-only paginated listing of all users.
- PATCH /users/{id}/status: Admin-only toggle to activate or deactivate a user account.
  Includes Admin Self-Lock Guard (admin cannot disable their own account).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_admin
from app.models.user import User
from app.repositories import user_repo
from app.schemas.pagination import PageResponse
from app.schemas.user import UserResponse, UserStatusRequest, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    response_description="The authenticated user's record",
)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Retrieve the profile of the currently authenticated user.

    Requires a valid Clerk Bearer JWT token.
    Enforces Soft-Disable Active Guard via get_current_user.
    """
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    response_description="The updated user record",
)
async def update_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: UserUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Update profile fields for the authenticated user (e.g. full_name).

    Only fields provided in UserUpdateRequest will be updated.
    Does not allow users to modify their email, role, or active status.
    """
    updated_user = await user_repo.update(db, current_user, payload)
    return updated_user


@router.get(
    "",
    response_model=PageResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List all users (Admin only)",
    response_description="A paginated list of user records",
)
async def list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
) -> PageResponse[UserResponse]:
    """
    Retrieve a paginated list of all users, ordered by created_at descending.

    **RBAC:** Restricted to ADMIN role only. Non-admin users receive 403 Forbidden.
    """
    return await user_repo.get_all(db, page=page, size=size)


@router.patch(
    "/{id}/status",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user status (Admin only)",
    response_description="The updated user record with new active status",
)
async def set_user_status(
    id: uuid.UUID,
    payload: UserStatusRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Activate or deactivate a user account.

    **RBAC:** Restricted to ADMIN role only.
    **Admin Self-Lock Guard:** An administrator cannot disable their own account.
    Attempting to disable oneself returns HTTP 403 Forbidden.
    """
    # Admin Self-Lock Guard: Prevent admin from deactivating their own account
    if admin.id == id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cannot disable themselves",
        )

    target_user = await user_repo.get_by_id(db, id)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated_user = await user_repo.set_status(db, target_user, payload.is_active)
    return updated_user
