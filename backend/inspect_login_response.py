import asyncio
from app.core.config import settings
from app.core.database import init_database
from app.features.sessions.service import SessionService
from app.features.sessions.schemas import SessionCreateRequest
from app.features.agent.stealth import StealthManager

async def main():
    await init_database()
    
    session_data = SessionCreateRequest(
        name="Inspect-Login",
        stealth_mode="ultra"
    )
    api_keys = {
        "proxy_username": settings.WEBSHARE_PROXY_USERNAME,
        "proxy_password": settings.WEBSHARE_PROXY_PASSWORD,
    }
    
    print("Creating session...")
    session = await SessionService.create_session("6a551bae77b974912f7b940a", session_data, api_keys)
    session_id = str(session.id)
    
    context = SessionService.get_context(session_id)
    page = await context.new_page()
    
    url = "https://www.linkedin.com/login"
    print(f"Navigating to {url}...")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3)
    
    # Enter email
    print("Typing credentials...")
    await page.fill("input[type='email']:visible", "aakashsolanki0928@gmail.com")
    await asyncio.sleep(1)
    
    # Enter password
    await page.fill("input[type='password']:visible", "En21cs301065")
    await asyncio.sleep(1)
    
    # Click Sign In
    print("Clicking Sign In...")
    await page.click("button[type='submit']")
    
    print("Waiting 15 seconds for login response...")
    await asyncio.sleep(15)
    
    # Check URL and save screenshot/content
    print("Final URL:", page.url)
    print("Final Title:", await page.title())
    
    screenshot_filepath = "/app/logs/login_result_screenshot.png"
    await page.screenshot(path=screenshot_filepath)
    print(f"Screenshot saved to {screenshot_filepath}")
    
    content = await page.content()
    html_filepath = "/app/logs/login_result.html"
    with open(html_filepath, "w") as f:
        f.write(content)
    print(f"HTML saved to {html_filepath}")
    
    await SessionService.close_session(session_id, "6a551bae77b974912f7b940a")

if __name__ == "__main__":
    asyncio.run(main())
