"""Quick HITL test to verify the improved planner and file-based signals."""
import asyncio
from backend.agents.planner import parse_natural_language_to_json

async def test_hitl_normalization():
    """Test that 2FA steps are normalized to 'wait' action."""

    test_text = """Test: Salesforce Login with 2FA

URL: https://orgfarm-9a1de3d5e8-dev-ed.develop.my.salesforce.com

Test Steps:
1. Fill username "test@example.com" in Username field
2. Fill password "password123" in Password field
3. Click "Log In" button
4. WAIT for manual 2FA verification
5. Click "Home" link

Expected: Login successful after 2FA verification
"""

    result = await parse_natural_language_to_json(test_text)

    print("\n" + "="*70)
    print("HITL Normalization Test Results")
    print("="*70)

    for tc in result.get("testcases", []):
        print(f"\nTest Case: {tc.get('title')}")
        for i, step in enumerate(tc.get("steps", [])):
            action = step.get("action")
            target = step.get("target")
            value = step.get("value", "")
            marker = "[WAIT]" if action == "wait" else "      "
            print(f"{marker} Step {i+1}: action={action:12} target={target:30} value={value}")

    # Check if step 4 was normalized to wait
    step4 = result["testcases"][0]["steps"][3]  # 0-indexed
    assert step4["action"] == "wait", f"Expected 'wait' but got '{step4['action']}'"

    print(f"\n✅ SUCCESS: Step 4 correctly normalized to 'wait' action")
    print(f"   Target: {step4.get('target')}")
    print(f"   Value: {step4.get('value')}")

    return result

if __name__ == "__main__":
    asyncio.run(test_hitl_normalization())
