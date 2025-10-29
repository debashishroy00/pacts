#!/usr/bin/env python
"""
Integration test: SauceDemo login flow
Tests the complete pipeline: Planner → POMBuilder → Executor
"""
import asyncio
import json
from backend.graph.state import RunState
from backend.graph.build_graph import ainvoke_graph
from backend.runtime.browser_manager import BrowserManager


async def test_saucedemo_login():
    """Test SauceDemo login with full pipeline."""
    print("\n" + "="*80)
    print("PACTS Integration Test: SauceDemo Login")
    print("="*80)

    state = RunState(
        req_id="REQ-SAUCEDEMO-001",
        context={
            "url": "https://www.saucedemo.com",
            "raw_steps": [
                "Username@LoginForm | fill | standard_user",
                "Password@LoginForm | fill | secret_sauce",
                "Login@LoginForm | click"
            ]
        }
    )

    print("\n[1/4] Initial State:")
    print(f"  • Request ID: {state.req_id}")
    print(f"  • URL: {state.context['url']}")
    print(f"  • Steps: {len(state.context['raw_steps'])}")

    try:
        print("\n[2/4] Running LangGraph Pipeline...")
        print("  • Planner: Parsing intents")
        print("  • POMBuilder: Discovering selectors")
        print("  • Executor: Running actions")

        result_dict = await ainvoke_graph(state)

        # LangGraph returns AddableValuesDict, convert back to RunState
        result = RunState(**result_dict)

        print("\n[3/4] Pipeline Results:")
        print(f"  • Final Step Index: {result.step_idx}/{len(result.plan)}")
        print(f"  • Verdict: {result.verdict}")
        print(f"  • Failure: {result.failure.value}")
        print(f"  • Heal Rounds: {result.heal_round}")

        if "plan" in result.context:
            print(f"\n[4/4] Discovered Plan ({len(result.plan)} steps):")
            for i, step in enumerate(result.plan):
                print(f"\n  Step {i+1}:")
                print(f"    • Element: {step.get('element', 'N/A')}")
                print(f"    • Action: {step.get('action', 'N/A')}")
                print(f"    • Selector: {step.get('selector', 'N/A')}")
                print(f"    • Confidence: {step.get('confidence', 0.0):.2f}")
                if step.get('meta'):
                    print(f"    • Strategy: {step['meta'].get('strategy', 'N/A')}")

        if "executed_steps" in result.context:
            print(f"\n  Executed Steps: {len(result.context['executed_steps'])}")
            for i, exec_step in enumerate(result.context["executed_steps"]):
                print(f"    {i+1}. {exec_step['action']} on {exec_step['selector']}")

        if "rca" in result.context:
            print(f"\n  Root Cause Analysis:")
            print(f"    {result.context['rca']}")

        print("\n" + "="*80)
        if result.verdict == "pass":
            print("[PASS] TEST PASSED: All steps executed successfully!")
        elif result.verdict == "fail":
            print("[FAIL] TEST FAILED: Check RCA above")
        else:
            print("[PARTIAL] TEST PARTIAL: Some steps completed")
        print("="*80)

        return result

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # Cleanup browser
        print("\n[Cleanup] Shutting down browser...")
        await BrowserManager.shutdown()


if __name__ == "__main__":
    result = asyncio.run(test_saucedemo_login())
    if result:
        print("\nFinal state saved to: saucedemo_result.json")
        with open("saucedemo_result.json", "w") as f:
            json.dump(result.model_dump(), f, indent=2)
