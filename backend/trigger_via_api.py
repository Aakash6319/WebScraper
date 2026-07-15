import sys
import os
import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import init_database
from app.features.auth.models import UserDocument
from app.core.security import create_access_token

async def main():
    await init_database()
    
    # Get user
    user = await UserDocument.get("6a551bae77b974912f7b940a")
    
    if not user:
        print("User 6a551bae77b974912f7b940a not found, falling back to first user")
        user = await UserDocument.find_all().first_or_none()
    
    if not user:
        print("No user found in DB!")
        return
        
    print(f"Using User: {user.email} (ID: {user.id})")
    
    # Match the SECRET_KEY used in the Docker compose file
    from app.core.config import settings
    settings.SECRET_KEY = "change-me-in-production"
    
    # Generate JWT token
    token = create_access_token(subject=str(user.id))
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": "Go to linkedin.com, log in with email: aakashsolanki0928@gmail.com and password: En21cs301065, then search for \"Python Developer\" jobs in India, apply to a job using Easy Apply with these details - Name: Aakash Solanki, Phone: +91 9876543210, Experience: 3 years, Title: Python Developer. After applying, show the job title and company name.",
        "priority": 1,
        "max_retries": 2,
        "timeout_seconds": 600
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        print("Sending task creation request to backend API...")
        response = await client.post("http://localhost:8000/api/v1/tasks", json=payload, headers=headers)
        if response.status_code == 201:
            task_data = response.json()
            print("🎉 Task created successfully!")
            print(f"Task ID: {task_data.get('id')}")
            print(f"Status: {task_data.get('status')}")
            print(f"Prompt: {task_data.get('prompt')}")
        else:
            print(f"❌ Failed to create task: Status {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    asyncio.run(main())
