import asyncio
from app.core.database import init_database
from app.features.sessions.service import SessionService

async def main():
    await init_database()
    session_id = "6a562a3e498b664f607866f2"
    context = SessionService._active_contexts.get(session_id)
    if not context:
        print("Active context not found in memory!")
        return
        
    pages = context.pages
    if not pages:
        print("No active pages in context!")
        return
        
    page = pages[0]
    print("Page URL:", page.url)
    
    html = await page.content()
    # Save the HTML to check it
    with open("/app/challenge_page.html", "w") as f:
        f.write(html)
    print("Successfully saved challenge_page.html")
    
    # Print forms and buttons
    elements = await page.evaluate("""
        () => {
            const forms = Array.from(document.querySelectorAll('form')).map(f => ({
                id: f.id,
                action: f.action,
                class: f.className,
                inputs: Array.from(f.querySelectorAll('input, textarea')).map(i => ({
                    name: i.name,
                    id: i.id,
                    type: i.type,
                    value: i.value ? i.value.slice(0, 30) : ''
                }))
            }));
            const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]')).map(b => ({
                id: b.id,
                text: b.innerText || b.value,
                class: b.className
            }));
            return { forms, buttons };
        }
    """)
    print("Forms:", elements["forms"])
    print("Buttons:", elements["buttons"])

if __name__ == "__main__":
    asyncio.run(main())
