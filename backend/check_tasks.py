import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.features.tasks.models import TaskDocument

async def main():
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        # Test connection
        await client.admin.command('ping')
    except Exception as e:
        # Fallback to docker container hostname if run inside docker network
        try:
            client = AsyncIOMotorClient("mongodb://mongodb:27017", serverSelectionTimeoutMS=2000)
            await client.admin.command('ping')
        except Exception:
            print("Could not connect to MongoDB. Make sure containers are running.")
            return

    await init_beanie(database=client.autowebagent, document_models=[TaskDocument])
    
    # Get latest tasks
    tasks = await TaskDocument.find_all().sort("-created_at").limit(5).to_list()
    if not tasks:
        print("No tasks found in database.")
        return
        
    print("\n--- LATEST TASKS STATUS ---")
    for t in tasks:
        print(f"\nTask ID: {t.id}")
        print(f"Prompt: {t.prompt}")
        print(f"Status: {t.status.upper()}")
        print(f"Steps Executed: {t.current_step} / {t.total_steps}")
        if t.error_message:
            print(f"Error Message: {t.error_message}")
        if t.steps_executed:
            print("Last Step Details:")
            last_step = t.steps_executed[-1]
            print(f"  - Action: {last_step.get('action')}")
            print(f"  - Status: {last_step.get('status')}")
            print(f"  - Description: {last_step.get('description')}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())
