"""
AutoWebAgent - Superadmin Seed Script
======================================
Run inside container: docker exec autowebagent-backend python /app/seed_superadmin.py
"""
import asyncio, os, sys
sys.path.insert(0, '/app')

from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.features.auth.models import UserDocument, UserRole
from app.core.security import hash_password

# ── Default Superadmin Credentials ──────────────────────
EMAIL = "admin@autowebagent.com"
USERNAME = "superadmin"
PASSWORD = "Admin@123456"
FULLNAME = "Super Admin"
# ────────────────────────────────────────────────────────

async def main():
    client = AsyncIOMotorClient("mongodb://mongodb:27017")
    db = client["autowebagent"]

    await init_beanie(database=db, document_models=[UserDocument])

    existing = await UserDocument.find_one(UserDocument.email == EMAIL)
    if existing:
        print(f"Already exists: {EMAIL}")
        client.close()
        return

    user = UserDocument(
        email=EMAIL,
        username=USERNAME,
        full_name=FULLNAME,
        hashed_password=hash_password(PASSWORD),
        role=UserRole.SUPERADMIN,
        is_active=True,
        is_verified=True,
        email_verified_at=datetime.now(timezone.utc),
    )
    await user.insert()
    client.close()

    print("=" * 50)
    print("  SUPERADMIN CREATED!")
    print("=" * 50)
    print(f"  Email:    {EMAIL}")
    print(f"  Username: {USERNAME}")
    print(f"  Password: {PASSWORD}")
    print(f"  Role:     superadmin")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
