"""Script to promote or manage user roles in Cocoloco database.

Usage:
    uv run python scripts/promote_admin.py <email_or_clerk_id> [ADMIN|USER]
"""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole


async def set_user_role(identifier: str, role_str: str = "ADMIN") -> bool:
    target_role = UserRole.ADMIN if role_str.upper() == "ADMIN" else UserRole.USER
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                (User.email == identifier) | (User.clerk_id == identifier)
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            print(f"❌ User with email or clerk_id '{identifier}' not found in database.")
            return False

        old_role = user.role.value
        user.role = target_role
        await db.commit()
        print(
            f"✅ Success! User '{user.full_name}' ({user.email}) role changed: "
            f"{old_role} ➔ {user.role.value}"
        )
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/promote_admin.py <email_or_clerk_id> [ADMIN|USER]")
        sys.exit(1)

    target_identifier = sys.argv[1]
    role_arg = sys.argv[2] if len(sys.argv) > 2 else "ADMIN"
    asyncio.run(set_user_role(target_identifier, role_arg))
