import asyncio
import sys
import os

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
    print(f"Task ID: {t.id}")
    print(f"Goal: {t.prompt}")
    print(f"Status: {t.status}")
    print(f"Extracted Data: {t.extracted_data}")
    print(f"Steps: {len(t.steps_executed)}")
    for i, s in enumerate(t.steps_executed):
        print(f"  [{i+1}] {s.get('action')} - {s.get('description')[:50]} (Success: {s.get('success')})")

if __name__ == "__main__":
    asyncio.run(main())
