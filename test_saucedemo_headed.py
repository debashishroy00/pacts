#!/usr/bin/env python
"""
Integration test: SauceDemo login flow with HEADED browser
Run this to watch PACTS discover and execute steps in a visible browser!
"""
import asyncio
import json
from backend.graph.state import RunState
from backend.runtime.browser_client import BrowserClient
from backend.agents import planner, pom_builder, executor
from backend.graph.build_graph import should_heal


async def test_saucedemo_headed():
    """Test SauceDemo login with visible browser."""
    print("\n" + "="*80)
    print("PACTS HEADED TEST: Watch the browser automation!")
    print("="*80)

    # Create browser client with headed mode
    browser = BrowserClient()
    await browser.start(headless=False)  # headless=False shows the browser!

    print("\n[Browser launched in HEADED mode - you should see it open!]")

    try:
        state = RunState(
            req_id="REQ-SAUCEDEMO-HEADED",
            context={
                "url": "https://www.saucedemo.com",
                "raw_steps": [
                    "Username@LoginForm | fill | standard_user",
                    "Password@LoginForm | fill | secret_sauce",
                    "Login@LoginForm | click"
                ]
            }
        )

        print("\n" + "-"*80)
        print("[STEP 1/4] PLANNER: Parsing requirements...")
        print("-"*80)
        state = await planner.run(state)
        print(f"  -> Parsed {len(state.context['intents'])} intents")
        for i, intent in enumerate(state.context['intents']):
            print(f"     {i+1}. {intent['element']} | {intent['action']} | {intent.get('value', 'N/A')}")

        print("\n" + "-"*80)
        print("[STEP 2/4] POM BUILDER: Discovering selectors...")
        print("-"*80)
        print("  -> Navigating to https://www.saucedemo.com")
        await browser.goto(state.context["url"])
        print("  -> Page loaded! Starting discovery...")

        # Manually run discovery (since we're not using BrowserManager singleton)
        from backend.runtime.discovery import discover_selector
        plan = []
        for i, intent in enumerate(state.context.get("intents", [])):
            print(f"\n  [{i+1}/{len(state.context['intents'])}] Discovering: {intent['element']}")
            cand = await discover_selector(browser, intent)
            if cand:
                plan.append({
                    **intent,
                    "selector": cand["selector"],
                    "meta": cand.get("meta", {}),
                    "confidence": cand.get("score", 0.0)
                })
                strategy = cand["meta"].get("strategy", "unknown")
                confidence = cand.get("score", 0.0)
                print(f"     -> FOUND: {cand['selector']} (strategy={strategy}, confidence={confidence:.2f})")
            else:
                print(f"     -> NOT FOUND (will skip)")

        state.context["plan"] = plan
        print(f"\n  -> Discovery complete! Found {len(plan)}/{len(state.context['intents'])} selectors")

        print("\n" + "-"*80)
        print("[STEP 3/4] EXECUTOR: Running actions...")
        print("-"*80)
        print("  [Watch the browser - you'll see form fields being filled!]\n")

        # Manually execute steps (since we're not using graph)
        from backend.runtime.policies import five_point_gate

        for step_idx, step in enumerate(plan):
            selector = step.get("selector")
            action = step.get("action", "click")
            value = step.get("value")

            print(f"  [{step_idx+1}/{len(plan)}] {action.upper()}: {step['element']}")
            print(f"     Selector: {selector}")

            # Validate with five-point gate
            el = await browser.query(selector)
            if not el:
                print(f"     -> ERROR: Element not found!")
                continue

            gates = await five_point_gate(browser, selector, el)
            print(f"     Gates: unique={gates['unique']}, visible={gates['visible']}, "
                  f"enabled={gates['enabled']}, stable={gates['stable_bbox']}")

            if not all(gates.values()):
                print(f"     -> VALIDATION FAILED!")
                continue

            # Perform action
            try:
                locator = browser.page.locator(selector)
                if action == "fill":
                    print(f"     -> Filling with: {value}")
                    await locator.fill(value, timeout=5000)
                    await asyncio.sleep(0.5)  # Pause so you can see it
                elif action == "click":
                    print(f"     -> Clicking...")
                    await locator.click(timeout=5000)
                    await asyncio.sleep(1)  # Pause so you can see it
                print(f"     -> SUCCESS!")
            except Exception as e:
                print(f"     -> ERROR: {e}")

        print("\n" + "-"*80)
        print("[STEP 4/4] VERDICT")
        print("-"*80)

        # Check if we're on the inventory page (successful login)
        current_url = browser.page.url
        if "inventory.html" in current_url:
            print("  -> VERDICT: PASS")
            print("  -> You should see the Products page!")
            print(f"  -> Current URL: {current_url}")
        else:
            print("  -> VERDICT: FAIL")
            print(f"  -> Current URL: {current_url}")

        print("\n" + "="*80)
        print("[SUCCESS] Test completed! Browser will stay open for 10 seconds...")
        print("="*80)

        # Keep browser open so you can see the result
        await asyncio.sleep(10)

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[Closing browser...]")
        await browser.close()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Starting PACTS Headed Browser Test")
    print("="*80)
    print("\nThis test will:")
    print("  1. Open a VISIBLE Chrome browser window")
    print("  2. Navigate to SauceDemo")
    print("  3. Discover Username, Password, and Login button")
    print("  4. Fill in the form (you'll see it happen!)")
    print("  5. Click Login")
    print("  6. Keep browser open for 10 seconds so you can see the result")
    print("\nGet ready to watch the magic! 3... 2... 1...\n")

    asyncio.run(test_saucedemo_headed())

    print("\n[Test complete!]\n")
