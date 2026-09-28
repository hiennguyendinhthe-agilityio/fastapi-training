"""
app/api/deps.py
FastAPI dependency injection utilities.

Provides:
- get_db: Yields an async database session per request (from app.core.database).
- get_current_user: Clerk token verification and DB lookup (implemented in Task 3.4).
- require_admin: RBAC role verification guard (implemented in Task 3.4).
"""

from app.core.database import get_db

__all__ = [
    "get_db",
]
