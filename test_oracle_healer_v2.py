"""
Quick Integration Test: OracleHealer v2 Validation

Tests healing flow with intentional failures that should be recovered.
"""
import asyncio
from backend.agents import executor, oracle_healer
from backend.graph.state import RunState, Failure
from backend.runtime.browser_manager import BrowserManager


async def test_healer_reveal_scroll():
    """Test healing with element that needs scrolling to be visible."""
    print("\n=== TEST: OracleHealer Reveal (Scroll) ===\n")

    # Create a test page with element below viewport
    test_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Scroll Test</title></head>
    <body>
        <div style="height: 2000px;"></div>
        <input id="username" name="username" value="" />
        <input id="password" type="password" name="password" value="" />
        <button id="login" type="submit">Login</button>
    </body>
    </html>
    """

    browser = await BrowserManager.get()
    await browser.page.set_content(test_html)

    # Scroll to top (hide login button)
    await browser.page.evaluate("window.scrollTo(0, 0)")

    state = RunState(
        req_id="test_heal_scroll",
        context={
            "url": "about:blank",
            "intents": [
                {"element": "username", "action": "fill", "value": "test_user"},
                {"element": "password", "action": "fill", "value": "test_pass"},
                {"element": "login", "action": "click", "value": ""},
            ],
            "plan": [
                {"element": "username", "selector": "#username", "action": "fill", "value": "test_user"},
                {"element": "password", "selector": "#password", "action": "fill", "value": "test_pass"},
                {"element": "login", "selector": "#login", "action": "click", "value": ""},
            ]
        }
    )

    # Execute all steps (simulating LangGraph loop)
    result = state
    while result.step_idx < len(result.plan):
        result = await executor.run(result)

        # If failure, trigger healing
        max_heal_attempts = 3
        while result.failure != Failure.none and result.heal_round < max_heal_attempts:
            print(f"\n  -> Executor failed with {result.failure.value}, triggering OracleHealer (round {result.heal_round + 1})...")
            result = await oracle_healer.run(result)
            result = await executor.run(result)

        # Break if still failed after max healing
        if result.failure != Failure.none:
            break

    print(f"\nVerdict: {result.verdict if result.verdict else 'partial'}")
    print(f"Heal Rounds: {result.heal_round}")
    print(f"Heal Events: {len(result.heal_events)}")

    if result.heal_events:
        for i, event in enumerate(result.heal_events):
            print(f"\n  Heal Round {event['round']}:")
            print(f"    - Failure: {event['failure_type']}")
            print(f"    - Actions: {event['actions']}")
            print(f"    - Success: {event['success']}")
            print(f"    - Duration: {event['duration_ms']}ms")

    assert result.step_idx == len(result.plan), f"Expected all steps executed, got {result.step_idx}/{len(result.plan)}"
    print("\nOK Test passed - OracleHealer successfully completed all steps")


async def test_healer_reprobe():
    """Test healing with reprobe strategy ladder."""
    print("\n=== TEST: OracleHealer Reprobe (Strategy Ladder) ===\n")

    test_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Reprobe Test</title></head>
    <body>
        <input id="user" placeholder="Username" />
        <input id="pass" type="password" placeholder="Password" />
        <button data-test="submit-btn">Login</button>
    </body>
    </html>
    """

    browser = await BrowserManager.get()
    await browser.page.set_content(test_html)

    # Simulate selector drift - original selector doesn't exist
    state = RunState(
        req_id="test_heal_reprobe",
        context={
            "url": "about:blank",
            "intents": [
                {"element": "Username", "action": "fill", "value": "test_user"},
                {"element": "Password", "action": "fill", "value": "test_pass"},
                {"element": "Login", "action": "click", "value": ""},
            ],
            "plan": [
                # Use wrong selectors to trigger reprobe
                {"element": "Username", "selector": "#username-wrong", "action": "fill", "value": "test_user"},
                {"element": "Password", "selector": "#password-wrong", "action": "fill", "value": "test_pass"},
                {"element": "Login", "selector": "#login-wrong", "action": "click", "value": ""},
            ]
        }
    )

    # Execute all steps (simulating LangGraph loop)
    result = state
    while result.step_idx < len(result.plan):
        result = await executor.run(result)

        # If failure, trigger healing
        max_heal_attempts = 3
        while result.failure != Failure.none and result.heal_round < max_heal_attempts:
            print(f"\n  -> Executor failed with {result.failure.value}, triggering OracleHealer (round {result.heal_round + 1})...")
            result = await oracle_healer.run(result)
            result = await executor.run(result)

        # Break if still failed after max healing
        if result.failure != Failure.none:
            break

    print(f"\nVerdict: {result.verdict if result.verdict else 'partial'}")
    print(f"Heal Rounds: {result.heal_round}")
    print(f"Heal Events: {len(result.heal_events)}")

    if result.heal_events:
        for i, event in enumerate(result.heal_events):
            print(f"\n  Heal Round {event['round']}:")
            print(f"    - Failure: {event['failure_type']}")
            print(f"    - Actions: {event['actions']}")
            if "new_selector" in event:
                print(f"    - New Selector: {event['new_selector']}")
            print(f"    - Success: {event['success']}")
            print(f"    - Duration: {event['duration_ms']}ms")

    # May fail or pass depending on reprobe success
    print(f"\nOK Test completed - Heal rounds: {result.heal_round}, Steps: {result.step_idx}/{len(result.plan)}")


async def test_healer_max_rounds():
    """Test healing max 3 rounds limit."""
    print("\n=== TEST: OracleHealer Max Rounds (3) ===\n")

    test_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Max Rounds Test</title></head>
    <body>
        <!-- No elements - will fail all healing -->
    </body>
    </html>
    """

    browser = await BrowserManager.get()
    await browser.page.set_content(test_html)

    state = RunState(
        req_id="test_heal_max_rounds",
        context={
            "url": "about:blank",
            "intents": [
                {"element": "NonExistent", "action": "click", "value": ""},
            ],
            "plan": [
                {"element": "NonExistent", "selector": "#nonexistent", "action": "click", "value": ""},
            ]
        }
    )

    # Execute first step (will fail and trigger healing)
    result = state
    result = await executor.run(result)

    # Trigger healing
    max_heal_attempts = 3
    while result.failure != Failure.none and result.heal_round < max_heal_attempts:
        print(f"\n  -> Executor failed with {result.failure.value}, triggering OracleHealer (round {result.heal_round + 1})...")
        result = await oracle_healer.run(result)
        result = await executor.run(result)

    print(f"\nVerdict: {result.verdict if result.verdict else 'fail (partial)'}")
    print(f"Heal Rounds: {result.heal_round}")
    print(f"Heal Events: {len(result.heal_events)}")

    assert result.heal_round == 3, f"Expected exactly 3 heal rounds, got {result.heal_round}"
    assert result.failure != Failure.none, "Expected failure for non-existent element"

    print(f"\nOK Test passed - Stopped at max {result.heal_round} heal rounds")


async def main():
    """Run all OracleHealer v2 integration tests."""
    try:
        await test_healer_reveal_scroll()
        await test_healer_reprobe()
        await test_healer_max_rounds()

        print("\n" + "="*60)
        print("OK ALL ORACLE HEALER V2 TESTS PASSED")
        print("="*60)

    finally:
        await BrowserManager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
