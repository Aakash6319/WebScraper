import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.features.tasks.models import TaskDocument

async def main():
    client = AsyncIOMotorClient("mongodb://mongodb:27017")
    await init_beanie(database=client.autowebagent, document_models=[TaskDocument])
    t = await TaskDocument.get("6a58d73c84900e06cb157fae")
    if t:
        print("PROMPT:", t.prompt)
        print("STATUS:", t.status)
        print("ERROR:", t.error_message)
        print("CAPTCHA DETECTED:", t.captcha_detected)
        print("CAPTCHA SOLVED:", t.captcha_solved)
        print("EXTRACTED DATA:", t.extracted_data)
        if hasattr(t, "steps"):
            for s in t.steps:
                print(f"- Step {s.step}: {s.action} - success={s.success} - error={s.error}")
        elif hasattr(t, "execution_steps"):
            for s in t.execution_steps:
                print(f"- Step {s.get('step')}: {s.get('action')} - success={s.get('success')} - clicked={s.get('clicked') or s.get('typed') or s.get('url')}")
    else:
        print("Task not found")

asyncio.run(main())
