import asyncio, os, sys, json
from pathlib import Path
from playwright.async_api import async_playwright

SAVE_TO = Path("hitl/salesforce_auth.json")
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

        # Auto-detect successful login by waiting for Lightning UI
        timeout = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()

        print(f"[SF] Waiting for login + 2FA to complete...")

        while True:
            await asyncio.sleep(3)
            current_url = page.url

            # Wait for Lightning UI to actually load (not just URL change)
            # Check for specific Lightning elements that only appear after full login
            is_on_sf_domain = ".my.salesforce.com" in current_url or ".lightning.force.com" in current_url
            not_on_login_page = "login.salesforce.com" not in current_url

            if is_on_sf_domain and not_on_login_page:
                # Additional check: Wait for App Launcher or other Lightning UI elements
                try:
                    # Wait for Lightning UI to fully load (App Launcher button)
                    await page.wait_for_selector('button[title*="App Launcher"], button.appLauncher', timeout=5000)
                    print(f"[SF] ✓ Login + 2FA complete! (URL: {current_url[:60]}...)")
                    break
                except:
                    # App launcher not found yet, keep waiting (might still be in 2FA)
                    print(f"[SF] Still waiting (detected URL change but Lightning UI not ready)...")
                    pass

            # Timeout check
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                print(f"[SF] ✗ Timeout waiting for login ({timeout}s)")
                await browser.close()
                sys.exit(1)

        # Wait a bit more for session to fully establish
        await asyncio.sleep(3)

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
