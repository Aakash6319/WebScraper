import asyncio
from app.core.config import settings
from app.core.database import init_database
from app.features.sessions.service import SessionService
from app.features.sessions.schemas import SessionCreateRequest

async def main():
    # Initialize database connection
    await init_database()
    
    # Start a dummy session with stealth
    session_data = SessionCreateRequest(
        name="Inspect-LinkedIn",
        stealth_mode="ultra"
    )
    # We will use the settings/env proxy credentials
    api_keys = {
        "proxy_username": settings.WEBSHARE_PROXY_USERNAME,
        "proxy_password": settings.WEBSHARE_PROXY_PASSWORD,
    }
    
    print("Creating session...")
    session = await SessionService.create_session("6a551bae77b974912f7b940a", session_data, api_keys)
    session_id = str(session.id)
    print(f"Session created: {session_id}")
    
    # Get browser context
    context = SessionService.get_context(session_id)
    page = await context.new_page()
    
    url = "https://www.linkedin.com/login"
    print(f"Navigating to {url}...")
    await page.goto(url, wait_until="networkidle")
    
    print("Page loaded! URL:", page.url)
    
    # Dump the HTML content to the logs folder (which is mounted to host)
    content = await page.content()
    html_filepath = "/app/logs/linkedin_login.html"
    with open(html_filepath, "w") as f:
        f.write(content)
    print(f"HTML saved to {html_filepath}")
    
    # Screenshot
    screenshot_filepath = "/app/logs/linkedin_login_screenshot.png"
    await page.screenshot(path=screenshot_filepath)
    print(f"Screenshot saved to {screenshot_filepath}")
    
    # Print input fields info
    inputs = await page.query_selector_all("input")
    print(f"Found {len(inputs)} inputs:")
    for idx, inp in enumerate(inputs):
        id_val = await inp.get_attribute("id")
        name_val = await inp.get_attribute("name")
        type_val = await inp.get_attribute("type")
        print(f"  [{idx+1}] id={id_val}, name={name_val}, type={type_val}")
        
    # Clean up
    await SessionService.close_session(session_id, "6a551bae77b974912f7b940a")

if __name__ == "__main__":
    asyncio.run(main())
