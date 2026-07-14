import asyncio
from app.core.database import init_database
from app.features.sessions.service import SessionService
from loguru import logger

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
    print("Page Title:", await page.title())
    
    # Check textareas in all frames
    for i, frame in enumerate(page.frames):
        try:
            print(f"\n--- Frame {i} (URL: {frame.url}) ---")
            elements_info = await frame.evaluate("""
                () => {
                    const textareas = document.querySelectorAll('textarea');
                    const inputs = document.querySelectorAll('input');
                    const result = [];
                    for (const t of textareas) {
                        result.push({
                            type: 'textarea',
                            name: t.getAttribute('name'),
                            id: t.getAttribute('id'),
                            class: t.getAttribute('class'),
                            value_len: t.value ? t.value.length : 0,
                            value_preview: t.value ? t.value.slice(0, 30) : ''
                        });
                    }
                    for (const inp of inputs) {
                        if (inp.getAttribute('type') === 'hidden' || inp.getAttribute('name') === 'captchaUserResponseToken') {
                            result.push({
                                type: 'input',
                                name: inp.getAttribute('name'),
                                id: inp.getAttribute('id'),
                                class: inp.getAttribute('class'),
                                value_len: inp.value ? inp.value.length : 0,
                                value_preview: inp.value ? inp.value.slice(0, 30) : ''
                            });
                        }
                    }
                    return result;
                }
            """)
            print("Elements:", elements_info)
        except Exception as e:
            print(f"Error checking frame {i}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
