"""Test that planner adds 'within' hints correctly."""
import asyncio
from backend.agents.planner import parse_natural_language_to_json

async def test():
    text = """Test: Salesforce Navigation

URL: https://salesforce.com

Test Steps:
1. Click "App Launcher" button
2. Click "Accounts" link
3. Click "New" button
"""
    
    result = await parse_natural_language_to_json(text)
    
    print("\n=== Test Cases ===")
    for tc in result.get("testcases", []):
        print(f"\nTest: {tc.get('title')}")
        for i, step in enumerate(tc.get("steps", [])):
            within = step.get("within", "N/A")
            print(f"  Step {i}: {step.get('action')} '{step.get('target')}' | within={within}")

asyncio.run(test())
