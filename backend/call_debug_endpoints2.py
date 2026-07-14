import asyncio
import httpx
import time
from app.core.database import init_database
from app.features.tasks.models import TaskDocument
from app.core.security import create_access_token
from bson import ObjectId

async def main():
    await init_database()
    task = await TaskDocument.get(ObjectId("6a562a3c498b664f607866f1"))
    if not task:
        print("Task not found!")
        return
        
    user_id = str(task.user_id)
    print(f"Task ID: {task.id}, User ID: {user_id}")
    
    # Generate JWT token
    token = create_access_token(subject=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=30) as client:
        for loop in range(6):
            print(f"[{time.strftime('%H:%M:%S')}] Attempt {loop + 1}/6...")
            
            # Get debug text
            url_text = f"http://localhost:8000/api/v1/tasks/{task.id}/debug-text"
            resp_text = await client.get(url_text, headers=headers)
            if resp_text.status_code == 200:
                data = resp_text.json()
                print("  URL:", data.get("url"))
                print("  Title:", data.get("title"))
            
            # Get debug screenshot
            url_ss = f"http://localhost:8000/api/v1/tasks/{task.id}/debug-screenshot"
            resp_ss = await client.get(url_ss, headers=headers)
            if resp_ss.status_code == 200:
                with open(f"/app/flow_{loop}.png", "wb") as f:
                    f.write(resp_ss.content)
                print(f"  Saved flow_{loop}.png")
            else:
                print("  Failed to get debug screenshot:", resp_ss.text[:120])
                
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
