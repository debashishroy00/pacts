import asyncio, os, sys, json
from pathlib import Path
from playwright.async_api import async_playwright

SAVE_TO = Path("hitl/salesforce_auth.json")  # same file PACTS expects
URL = os.getenv("SF_LOGIN_URL", "").strip() or "https://login.salesforce.com"
SLOW_MO = int(os.getenv("SF_SLOW_MO", "1000"))

async def main():
    SAVE_TO.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=SLOW_MO)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        print(f"\n{'='*70}")
        print(f"  SALESFORCE LOGIN REQUIRED")
        print(f"{'='*70}")
        print(f"\n[SF] Opening: {URL}")
        await page.goto(URL, wait_until="domcontentloaded")

        print(f"\n  Please complete login in the browser window:")
        print(f"    1. Enter username")
        print(f"    2. Enter password")
        print(f"    3. Complete 2FA if prompted")
        print(f"\n  PACTS will auto-detect when you're logged in...")
        print(f"  (No need to create any files manually!)")
        print(f"\n{'='*70}\n")

        # Auto-detect successful login by waiting for non-login URL
        timeout = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()

        while True:
            await asyncio.sleep(2)
            current_url = page.url

            # Check if user successfully logged in (URL changed from login page)
            if "login.salesforce.com" not in current_url and "salesforce.com" in current_url:
                print(f"[SF] ✓ Login detected! (URL: {current_url[:60]}...)")
                break

            # Timeout check
            if asyncio.get_event_loop().time() - start_time > timeout:
                print(f"[SF] ✗ Timeout waiting for login ({timeout}s)")
                await browser.close()
                sys.exit(1)

        # Wait a bit more for session to fully establish
        await asyncio.sleep(2)

        # Save session
        await ctx.storage_state(path=str(SAVE_TO))
        await browser.close()
        print(f"[SF] ✓ Session saved to: {SAVE_TO.resolve()}")
        print(f"[SF] ✓ Session valid for ~2 hours\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
