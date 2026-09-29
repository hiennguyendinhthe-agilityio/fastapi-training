"""
app/api/deps.py
FastAPI dependency injection utilities for authentication and authorization.

Provides:
- get_db: Yields an async database session per request (from app.core.database).
- get_current_user: Extracts and verifies Clerk Bearer token, fetches User from DB,
  and enforces the Soft-Disable Active Guard (is_active check).
- require_admin: RBAC guard that restricts access to ADMIN role only.

Security contract (from .agents/rules/03-security-rbac.md):
- get_current_user raises HTTP 401 if token is missing or invalid.
- get_current_user raises HTTP 403 if the user's account is deactivated
  (is_active=False).
- require_admin raises HTTP 403 if the authenticated user's role is not ADMIN.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_clerk_token
from app.models.user import User, UserRole

# OAuth2 scheme: requires "Authorization: Bearer <token>" header.
# auto_error=False allows us to return a custom 401 (not FastAPI's default).
_bearer_scheme = HTTPBearer(auto_error=False)

__all__ = [
    "get_db",
    "get_current_user",
    "require_admin",
]


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Authenticate and return the current active User.

    Steps:
    1. Extract Bearer token from the Authorization header.
    2. Verify token via Clerk RS256 JWKS (raises 401 on failure).
    3. Extract clerk_id from `sub` claim.
    4. Lookup User in the database by clerk_id.
    5. Enforce Soft-Disable Active Guard: raise 403 if is_active is False.

    Raises:
        HTTPException(401): Missing or invalid Bearer token.
        HTTPException(403): User account is deactivated.
        HTTPException(404): Authenticated clerk_id has no matching DB record.
    """
    # Step 1: Guard against missing Authorization header
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 2: Verify the token via Clerk JWKS — raises 401 on failure
    payload = verify_clerk_token(credentials.credentials)

    # Step 3: Extract clerk_id from `sub` claim
    # verify_clerk_token already guarantees 'sub' is present
    clerk_id: str = payload["sub"]

    # Step 4: Lookup User in the database
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "User account not found. Please complete registration via /auth/sync."
            ),
        )

    # Step 5: Soft-Disable Active Guard
    # Even with a valid JWT, a deactivated user must be blocked immediately.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    RBAC guard: restrict access to ADMIN role only.

    Must be used as a FastAPI dependency on admin-only routes.

    Raises:
        HTTPException(403): Current user does not have ADMIN role.

    Returns:
        The authenticated User instance (for downstream use in the route handler).
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
