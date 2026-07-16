import asyncio
import sys
import os
import base64

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import init_database
from app.features.tasks.models import TaskDocument

async def main():
    await init_database()
    tasks = await TaskDocument.find_all().sort("-created_at").limit(1).to_list()
    if not tasks:
        print("No tasks found.")
        return
    t = tasks[0]
    if not t.screenshots:
        print("No screenshots in this task.")
        return
    
    last_shot = t.screenshots[-1]
    if last_shot.startswith("data:image"):
        last_shot = last_shot.split(",")[1]
    
    img_data = base64.b64decode(last_shot)
    target_path = "./task_new_screenshot.png"
    with open(target_path, "wb") as f:
        f.write(img_data)
    print(f"Saved screenshot to {target_path}")

if __name__ == "__main__":
    asyncio.run(main())
