import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, PydanticObjectId

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import init_database
from app.features.tasks.models import TaskDocument, TaskStatus
from app.features.auth.models import UserDocument
from app.features.agent.service import AgentService

async def main():
    # Initialize Beanie database connection
    await init_database()
    
    # Get the latest task
    latest_task = await TaskDocument.find_all().sort("-created_at").first_or_none()
    if not latest_task:
        print("No tasks found to replicate/run!")
        return
        
    print(f"Latest Task ID: {latest_task.id}")
    print(f"Prompt: {latest_task.prompt}")
    print(f"Original Status: {latest_task.status}")
    print(f"Creating a new copy of the task to run fresh...")
    
    # Clone task to a new TaskDocument
    new_task = TaskDocument(
        user_id=latest_task.user_id,
        prompt=latest_task.prompt,
        status=TaskStatus.PENDING,
        priority=latest_task.priority,
        max_retries=latest_task.max_retries,
        timeout_seconds=latest_task.timeout_seconds,
    )
    await new_task.insert()
    print(f"New Task created: {new_task.id}")
    
    print("Starting agent execution for this task...")
    try:
        await AgentService.execute_task(str(new_task.id), str(new_task.user_id))
        print("Agent execution call finished!")
        
        # Reload and check final status
        final_task = await TaskDocument.get(new_task.id)
        print(f"Final status: {final_task.status}")
        if final_task.error_message:
            print(f"Error message: {final_task.error_message}")
        if final_task.extracted_data:
            print(f"Extracted data: {final_task.extracted_data}")
    except Exception as e:
        print(f"Exception during run: {e}")

if __name__ == "__main__":
    asyncio.run(main())
