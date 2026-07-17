import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.features.tasks.models import TaskDocument

async def main():
    client = AsyncIOMotorClient("mongodb://mongodb:27017")
    await init_beanie(database=client.autowebagent, document_models=[TaskDocument])
    t = await TaskDocument.get("6a5933dfb4dafe1dd5008d7c")
    if t:
        print("PROMPT:", t.prompt)
        print("STATUS:", t.status)
        print("ERROR:", t.error_message)
        print("CAPTCHA DETECTED:", t.captcha_detected)
        print("CAPTCHA SOLVED:", t.captcha_solved)
        print("EXTRACTED DATA:", t.extracted_data)
        print("STEPS EXECUTED:")
        if hasattr(t, "steps_executed") and t.steps_executed:
            for i, s in enumerate(t.steps_executed):
                print(f"[{i+1}] {s.get('action')}: {s.get('description')} (Value: {s.get('value')})")
        else:
            print("None")
    else:
        print("Task not found")

asyncio.run(main())
