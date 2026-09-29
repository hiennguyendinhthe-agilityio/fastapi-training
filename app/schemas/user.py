"""
app/schemas/user.py
Pydantic v2 DTOs for User API responses and update requests.

Implemented in: Task 4.1 (full), partially bootstrapped in Task 3.5 for auth/sync.

DTOs:
- UserResponse: Public representation of a User record (id, email, full_name, role,
  is_active, created_at). Used as the response body for auth/sync and user endpoints.
- UserUpdateRequest: Partial update payload for the authenticated user's own profile.
- UserStatusRequest: Admin payload to enable/disable a user account.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserResponse(BaseModel):
    """
    Public representation of a User returned by API endpoints.

    Fields align with the User ORM model. `model_config` enables automatic
    conversion from SQLAlchemy ORM instances (from_attributes=True).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clerk_id: str
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    """
    Request body for PUT /api/v1/users/me.
    All fields are optional — only provided fields will be updated.
    """

    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        examples=["Nguyen Van A"],
    )


class UserStatusRequest(BaseModel):
    """
    Request body for PATCH /api/v1/users/{id}/status.
    Admin-only: enable or disable a user account.
    """

    is_active: bool = Field(
        ...,
        description="Set to true to activate, false to deactivate the user account.",
    )
