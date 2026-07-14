import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Configure with the user's proxy credentials to bypass geography blocks
        context = await browser.new_context(
            proxy={
                "server": "http://zkoanprw:fxg9gvct26g5@198.105.121.200:6462"
            }
        )
        page = await context.new_page()
        
        url = "https://www.linkedin.com/login"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        
        print("Page loaded! URL:", page.url)
        print("Page title:", await page.title())

        # Dump input fields attributes
        inputs = await page.query_selector_all("input")
        print(f"Found {len(inputs)} input fields:")
        for idx, inp in enumerate(inputs):
            tag = await inp.evaluate("el => el.tagName")
            id_val = await inp.get_attribute("id")
            name_val = await inp.get_attribute("name")
            type_val = await inp.get_attribute("type")
            placeholder = await inp.get_attribute("placeholder")
            class_val = await inp.get_attribute("class")
            print(f"[{idx+1}] tag={tag}, id={id_val}, name={name_val}, type={type_val}, placeholder={placeholder}, class={class_val}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
