import sys
import os
import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import init_database
from app.features.tasks.models import TaskDocument, TaskStatus
from app.features.auth.models import UserDocument
from app.core.security import create_access_token

async def main():
    await init_database()
    
    # Get latest task that is waiting for user input
    task = await TaskDocument.find_one(TaskDocument.status == TaskStatus.WAITING_USER_INPUT)
    if not task:
        # Fallback to the latest task overall
        task = await TaskDocument.find_all().sort("-created_at").first_or_none()
        
    if not task:
        print("No task found in database!")
        return
        
    print(f"Submitting OTP for Task ID: {task.id}")
    print(f"Prompt: {task.prompt}")
    
    # Get user
    user = await UserDocument.get(task.user_id)
    if not user:
        print("User not found!")
        return
        
    # Match the SECRET_KEY used in the Docker compose file
    from app.core.config import settings
    settings.SECRET_KEY = "change-me-in-production"
    
    # Generate JWT token
    token = create_access_token(subject=str(user.id))
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    otp = "028762"
    payload = {"value": otp}
    
    url = f"http://localhost:8000/api/v1/tasks/{task.id}/submit-input"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print("🎉 OTP submitted successfully!")
            print(response.json())
        else:
            print(f"❌ Failed to submit OTP: Status {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    asyncio.run(main())
