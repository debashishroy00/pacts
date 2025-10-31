"""
Generator Agent v2.0 - Test Artifact Generation

Consumes executed steps, heal events, and verdict to generate human-readable
Playwright test files with full healing annotations and confidence metadata.
"""
from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..graph.state import RunState
from ..telemetry.tracing import traced


def _sanitize_test_name(req_id: str) -> str:
    """Convert req_id to valid Python function name."""
    # Replace spaces, dashes, special chars with underscore
    sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in req_id)
    # Remove leading digits
    if sanitized and sanitized[0].isdigit():
        sanitized = "test_" + sanitized
    return sanitized.lower()


def _extract_strategies_used(plan: list) -> list[str]:
    """Extract unique discovery strategies from plan."""
    strategies = set()
    for step in plan:
        if "meta" in step and "strategy" in step["meta"]:
            strategies.add(step["meta"]["strategy"])
    return sorted(list(strategies))


def _enrich_steps_with_healing(plan: list, heal_events: list) -> list[dict]:
    """Enrich plan steps with healing information."""
    enriched = []

    for i, step in enumerate(plan):
        enriched_step = step.copy()
        enriched_step["healed"] = False
        enriched_step["heal_round"] = None
        enriched_step["heal_strategy"] = None

        # Find matching heal events for this step
        for event in heal_events:
            if event.get("step_idx") == i and event.get("success"):
                enriched_step["healed"] = True
                enriched_step["heal_round"] = event.get("round")
                # Extract heal strategy from actions
                actions = event.get("actions", [])
                heal_actions = [a for a in actions if "reprobe:" in a or "reveal" in a]
                enriched_step["heal_strategy"] = ", ".join(heal_actions) if heal_actions else "reveal"
                break

        enriched.append(enriched_step)

    return enriched


@traced("generator")
async def run(state: RunState) -> RunState:
    """
    Generator Agent v2.0: Generate Playwright test artifacts.

    Input:
        state.req_id: Test requirement ID
        state.context["url"]: Target URL
        state.context["plan"]: Verified selectors + metadata
        state.context.get("executed_steps", []): Execution log
        state.heal_events: Healing telemetry
        state.verdict: "pass" / "fail" / "partial"

    Output:
        - Writes test_<req_id>.py to generated_tests/
        - Updates state.context["generated_file"] with file path

    Returns:
        RunState with generation metadata
    """
    # Get template environment
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("test_template.j2")

    # Extract data from state
    req_id = state.req_id
    url = state.context.get("url", "about:blank")
    plan = state.context.get("plan", [])
    verdict = state.verdict or "partial"
    healed = state.heal_round > 0
    heal_rounds = state.heal_round

    # Enrich steps with healing information
    enriched_steps = _enrich_steps_with_healing(plan, state.heal_events)

    # Extract strategies used
    strategies_used = _extract_strategies_used(plan)

    # Generate test name
    test_name = _sanitize_test_name(req_id)
    test_description = f"Test for requirement: {req_id}"

    # Render template
    rendered = template.render(
        req_id=req_id,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        verdict=verdict,
        healed=healed,
        heal_rounds=heal_rounds,
        strategies_used=strategies_used,
        test_name=test_name,
        test_description=test_description,
        url=url,
        steps=enriched_steps
    )

    # Write to file
    output_dir = Path("generated_tests")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"test_{test_name}.py"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(rendered)

    # Update state with generation metadata
    state.context["generated_file"] = str(output_file)
    state.context["generated_at"] = datetime.now().isoformat()
    state.context["artifact_metadata"] = {
        "file": str(output_file),
        "test_name": test_name,
        "verdict": verdict,
        "healed": healed,
        "heal_rounds": heal_rounds,
        "strategies_used": strategies_used,
        "steps_count": len(enriched_steps)
    }

    return state
