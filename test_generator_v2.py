"""
Integration Test: Generator Agent v2.0

Tests artifact generation from executed steps with healing annotations.
"""
import asyncio
import os
from pathlib import Path
from backend.graph.build_graph import ainvoke_graph
from backend.graph.state import RunState
from backend.runtime.browser_manager import BrowserManager


async def test_generator_basic():
    """Test basic artifact generation from simple test flow."""
    print("\n=== TEST: Generator Basic Artifact Creation ===\n")

    # Create simple test requirements
    raw_steps = [
        "Username@LoginForm | fill | standard_user | field_populated",
        "Password@LoginForm | fill | secret_sauce | field_populated",
        "Login@LoginForm | click | | navigates_to:Products"
    ]

    state = RunState(
        req_id="saucedemo_login",
        context={
            "url": "https://www.saucedemo.com",
            "raw_steps": raw_steps
        }
    )

    # Run full graph (Planner -> POMBuilder -> Executor -> OracleHealer -> VerdictRCA -> Generator)
    graph_result = await ainvoke_graph(state)

    # Extract final RunState from LangGraph result
    result = graph_result if isinstance(graph_result, RunState) else RunState(**graph_result)

    print(f"Verdict: {result.verdict}")
    print(f"Generated File: {result.context.get('generated_file', 'N/A')}")

    # Validate artifact was created
    assert "generated_file" in result.context, "No generated file in context"
    generated_file = Path(result.context["generated_file"])
    assert generated_file.exists(), f"Generated file not found: {generated_file}"

    # Read and display artifact
    with open(generated_file, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"\n--- Generated Test Content ---")
    print(content[:500])  # First 500 chars
    print(f"... (total {len(content)} chars)")

    # Validate content structure
    assert "import asyncio" in content, "Missing import"
    assert "from playwright.async_api import async_playwright" in content, "Missing Playwright import"
    assert "async def test_" in content, "Missing test function"
    assert result.context.get("url", "") in content, "URL not in generated test"

    print("\nOK Test passed - Artifact generated successfully")


async def test_generator_with_healing():
    """Test artifact generation with healing annotations."""
    print("\n=== TEST: Generator With Healing Annotations ===\n")

    # Simulate test with healing (provide wrong selectors that will be healed)
    state = RunState(
        req_id="healed_test_example",
        context={
            "url": "https://example.com",
            "raw_steps": [
                "Username | fill | testuser | field_populated",
                "Submit | click | | navigates_to:Dashboard"
            ]
        }
    )

    # Manually create plan with healing simulation
    state.context["plan"] = [
        {
            "element": "Username",
            "action": "fill",
            "value": "testuser",
            "selector": "#username",
            "confidence": 0.88,
            "meta": {"strategy": "placeholder"}
        },
        {
            "element": "Submit",
            "action": "click",
            "value": "",
            "selector": "#submit-btn",
            "confidence": 0.95,
            "meta": {"strategy": "role_name"}
        }
    ]

    # Simulate healing event
    state.heal_events.append({
        "round": 1,
        "step_idx": 1,
        "failure_type": "not_visible",
        "actions": ["scroll_into_view", "dismiss_overlays(1)"],
        "success": True,
        "duration_ms": 2400
    })

    state.heal_round = 1
    state.verdict = "pass"
    state.context["healed"] = True

    # Run only Generator (skip full graph)
    from backend.agents import generator
    result = await generator.run(state)

    print(f"Generated File: {result.context.get('generated_file', 'N/A')}")

    # Validate healing annotations in artifact
    generated_file = Path(result.context["generated_file"])
    with open(generated_file, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"\n--- Healing Annotations ---")
    for line in content.split("\n"):
        if "HEALED" in line or "healed" in line.lower():
            print(f"  {line.strip()}")

    # Validate healing markers
    assert "HEALED" in content or "healed" in content.lower(), "Missing healing annotation"

    print("\nOK Test passed - Healing annotations present")


async def test_generator_metadata():
    """Test artifact metadata tracking."""
    print("\n=== TEST: Generator Metadata Tracking ===\n")

    state = RunState(
        req_id="metadata_test",
        context={
            "url": "https://example.com",
            "plan": [
                {
                    "element": "TestButton",
                    "action": "click",
                    "value": "",
                    "selector": "#test-btn",
                    "confidence": 0.90,
                    "meta": {"strategy": "role_name"}
                }
            ]
        }
    )

    state.verdict = "pass"

    # Run Generator
    from backend.agents import generator
    result = await generator.run(state)

    # Validate metadata
    assert "artifact_metadata" in result.context, "Missing artifact metadata"
    metadata = result.context["artifact_metadata"]

    print(f"\nArtifact Metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    # Validate metadata fields
    assert metadata["verdict"] == "pass", "Wrong verdict in metadata"
    assert metadata["healed"] == False, "Wrong healed status"
    assert metadata["steps_count"] == 1, "Wrong step count"
    assert len(metadata["strategies_used"]) > 0, "No strategies recorded"

    print("\nOK Test passed - Metadata tracked correctly")


async def main():
    """Run all Generator v2.0 integration tests."""
    try:
        # Test 1: Basic artifact generation (full graph)
        await test_generator_basic()

        # Test 2: Healing annotations
        await test_generator_with_healing()

        # Test 3: Metadata tracking
        await test_generator_metadata()

        print("\n" + "="*60)
        print("OK ALL GENERATOR V2.0 TESTS PASSED")
        print("="*60)

        # List generated artifacts
        print("\nGenerated Test Artifacts:")
        gen_dir = Path("generated_tests")
        if gen_dir.exists():
            for f in gen_dir.glob("*.py"):
                print(f"  - {f.name} ({f.stat().st_size} bytes)")

    finally:
        await BrowserManager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
