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
        print(f"[SF] Opening: {URL}")
        await page.goto(URL, wait_until="domcontentloaded")
        print("\n>>> Complete username + password + 2FA in the visible browser.")
        print(">>> After landing in Salesforce (Lightning home or any org page), type 'done' in session_done.txt")
        # Wait for signal file
        signal_file = Path("hitl/session_done.txt")
        signal_file.unlink(missing_ok=True)
        print(f">>> Waiting for signal file: {signal_file}")
        import time
        while not signal_file.exists():
            await asyncio.sleep(1)
        signal_file.unlink()
        await ctx.storage_state(path=str(SAVE_TO))
        await browser.close()
        print(f"[OK] Session saved to: {SAVE_TO.resolve()}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
