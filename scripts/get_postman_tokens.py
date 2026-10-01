"""Helper script to inspect users and guide Postman token configuration.

Usage:
    uv run python scripts/get_postman_tokens.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User


async def inspect_environment():
    print("=" * 65)
    print("🥐 COCOLOCO API — POSTMAN CONFIGURATION HELPER")
    print("=" * 65)

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).order_by(User.created_at))
        users = list(res.scalars().all())

    if not users:
        print("⚠️ No users found in database.")
        print("👉 Run `uv run python scripts/seed.py` or log in via Flutter app.")
        return

    print(f"\n📋 Found {len(users)} registered users in PostgreSQL:\n")
    for u in users:
        role_badge = "👑 ADMIN" if u.role.value == "ADMIN" else "👤 USER "
        print(f"  [{role_badge}] {u.email:<26} | Clerk ID: {u.clerk_id}")
        print(f"            UUID: {u.id} | Active: {u.is_active}\n")

    print("=" * 65)
    print("🔑 HOW TO GET REAL CLERK TOKENS FOR POSTMAN:")
    print("=" * 65)
    print("1. In Flutter App Console:")
    print("   Whenever you log in (via Clerk modal in Flutter), the app prints:")
    print("   '🔑 [CLERK TOKEN FOR POSTMAN (USER|ADMIN)]: eyJhbGciOiJSUzI1Ni...'")
    print("   👉 Copy that token string!")
    print()
    print("2. In Postman:")
    print("   Import: postman/Cocoloco_API.postman_collection.json")
    print("   Import: postman/Cocoloco_Local.postman_environment.json")
    print("   Select environment: 'Cocoloco Local'")
    print("   Paste your user token into 'user_token'")
    print("   Paste your admin token into 'admin_token'")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(inspect_environment())
