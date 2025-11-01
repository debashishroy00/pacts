import asyncio
from backend.runtime.discovery import discover_selector
from backend.runtime.browser_manager import BrowserManager

async def test():
    browser = await BrowserManager.get(config={"headless": False, "slow_mo": 500})
    await browser.goto("https://www.salesforce.com")
    
    # Test intent WITH within hint
    intent_with_within = {
        "element": "Accounts",
        "action": "click",
        "within": "App Launcher"
    }
    
    print("\n=== Testing discovery with 'within' hint ===")
    result = await discover_selector(browser, intent_with_within)
    print(f"Result: {result}")
    
    await browser.close()

asyncio.run(test())
