import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.features.auth.models import UserDocument
from app.core.security import encrypt_credential

async def main():
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    print(f"Connecting to MongoDB at {mongo_uri}...")
    try:
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=2000)
        # Test connection
        await client.admin.command('ping')
        print("Connected to MongoDB successfully!")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        print("Please make sure docker containers are running (docker compose up -d mongodb)")
        return

    await init_beanie(database=client.autowebagent, document_models=[UserDocument])
    
    # Find all users
    users = await UserDocument.find_all().to_list()
    print(f"Found {len(users)} user(s) in database.")
    if not users:
        print("No users found in database! Creating seed user admin@example.com...")
        from app.core.security import hash_password
        user = UserDocument(
            email="admin@example.com",
            username="admin",
            hashed_password=hash_password("Admin123"),
            full_name="Super Admin",
            role="superadmin",
            is_active=True,
            is_verified=True
        )
        users = [user]
        
    for user in users:
        print(f"Updating credentials for: {user.email}...")
        user.deepseek_api_key_encrypted = encrypt_credential("sk-5c8c555bccfb4b9eb8b24649df516a89")
        user.anticaptcha_api_key_encrypted = encrypt_credential("81823bd7a8f821102709de3601ed846e")
        user.capsolver_api_key_encrypted = encrypt_credential("CAP-F35972E69C6D5BF5C130A55A9FBD727989D73D4DA2E01770E252CC0714FC9495")
        user.webshare_proxy_username_encrypted = None
        user.webshare_proxy_password_encrypted = None
        user.proxy_host = None
        user.proxy_port = None
        await user.save()
        print(f"✅ Credentials successfully reset to use dynamic Webshare proxy pool for {user.email}!")

if __name__ == "__main__":
    asyncio.run(main())
