"""
Live test: Run the Page-Agent DOM parser on the actual LinkedIn login page
and verify the LLM can correctly identify the email and password fields.
"""
import asyncio
from app.core.database import init_database
from app.features.sessions.service import SessionService
from app.features.sessions.schemas import SessionCreateRequest
from app.features.agent.dom_parser import PageAgentDOMParser
from app.core.llm import LLMClient
from app.core.config import settings

async def main():
    await init_database()
    
    session_data = SessionCreateRequest(name="Test-DOM-Parser", stealth_mode="ultra")
    api_keys = {
        "proxy_username": settings.WEBSHARE_PROXY_USERNAME,
        "proxy_password": settings.WEBSHARE_PROXY_PASSWORD,
        "proxy_host": settings.WEBSHARE_PROXY_HOST,
        "proxy_port": settings.WEBSHARE_PROXY_PORT,
    }
    session = await SessionService.create_session("6a551bae77b974912f7b940a", session_data, api_keys)
    session_id = str(session.id)
    
    context = SessionService.get_context(session_id)
    page = await context.new_page()
    
    print("Navigating to LinkedIn login...")
    await page.goto(
        "https://www.linkedin.com/login",
        wait_until="domcontentloaded",
        timeout=60000
    )
    # Give a little extra time for React/SPA to render inputs
    import asyncio as _a
    await _a.sleep(3)
    print("Page URL:", page.url)
    
    # --- Page-Agent DOM Parsing ---
    print("\n=== Running Page-Agent DOM Parser ===")
    elements = await PageAgentDOMParser.get_interactive_elements(page)
    print(f"Found {len(elements)} interactive elements\n")
    
    dom_tree = PageAgentDOMParser.serialize_to_text(elements)
    print("DOM Tree:\n" + dom_tree + "\n")
    
    # --- LLM Resolution ---
    print("=== LLM Element Resolution ===")
    llm = LLMClient(user_api_key=settings.DEEPSEEK_API_KEY)
    
    # Test 1: Find email field
    decision1 = await llm.analyze_dom_action(
        dom_tree=dom_tree,
        action_description="Type the user's email or phone into the email/username login field",
        action_type="type",
        value="test@example.com"
    )
    print(f"Email field → [{decision1.get('element_index')}] (confidence={decision1.get('confidence')}) — {decision1.get('reason')}")
    
    # Test 2: Find password field
    decision2 = await llm.analyze_dom_action(
        dom_tree=dom_tree,
        action_description="Type the user's password into the password login field",
        action_type="type",
        value="my_password"
    )
    print(f"Password field → [{decision2.get('element_index')}] (confidence={decision2.get('confidence')}) — {decision2.get('reason')}")
    
    # Test 3: Find sign-in button
    decision3 = await llm.analyze_dom_action(
        dom_tree=dom_tree,
        action_description="Click the Sign In button to submit the login form",
        action_type="click",
    )
    print(f"Sign In button → [{decision3.get('element_index')}] (confidence={decision3.get('confidence')}) — {decision3.get('reason')}")
    
    # Verify: Actually try to fill element 
    if decision1.get('element_index'):
        locator = await PageAgentDOMParser.get_element_by_index(page, decision1['element_index'], elements)
        print(f"\nTesting fill on element [{decision1['element_index']}]...")
        await locator.fill("test_user@gmail.com")
        print("✅ Fill succeeded!")
    
    await SessionService.close_session(session_id, "6a551bae77b974912f7b940a")
    print("\n✅ Page-Agent DOM Parser test complete!")

if __name__ == "__main__":
    asyncio.run(main())
