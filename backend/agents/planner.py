from __future__ import annotations
from typing import Dict, Any, List
from ..graph.state import RunState
from ..telemetry.tracing import traced

def parse_steps(raw_steps: List[str]) -> List[Dict[str, Any]]:
    out = []
    for line in raw_steps:
        parts = [p.strip() for p in line.split("|")]
        er = parts[0].split("@")
        element = er[0].strip()
        region = er[1].strip() if len(er) > 1 else None
        action = parts[1].strip().lower() if len(parts) > 1 else "click"
        value = parts[2].strip().strip('"') if len(parts) > 2 else None
        out.append({
            "intent": f"{element}@{region}" if region else element,
            "element": element,
            "region": region,
            "action": action,
            "value": value
        })
    return out

@traced("planner")
async def run(state: RunState) -> RunState:
    """
    Planner Agent v2: Authoritative plan generation from suite JSON or legacy raw_steps.

    Priority:
    1. context["suite"] - Phase 2 authoritative JSON format (testcases, steps, data, outcomes)
    2. context["raw_steps"] - Phase 1 legacy pipe-delimited strings

    Outputs:
    - state.context["intents"] - Parsed step intents for POMBuilder
    - state.context["plan"] - Initial plan structure (updated by POMBuilder with selectors)
    - state.plan - Unified plan location
    """
    # PHASE 2: Authoritative suite JSON mode
    suite = state.context.get("suite")
    if suite:
        plan = []
        for tc in suite.get("testcases", []):
            data_rows = tc.get("data", [{}]) or [{}]  # Default to single row if no data
            for row in data_rows:
                for st in tc.get("steps", []):
                    step = {
                        "element": st.get("target"),
                        "action": st.get("action", "click").lower(),
                        "value": st.get("value", ""),
                        "expected": st.get("outcome"),
                        "meta": {"source": "planner_v2", "testcase": tc.get("id")}
                    }

                    # Bind template variables from data row (e.g., {{username}} → "testuser")
                    if step["value"]:
                        for var_name, var_value in row.items():
                            placeholder = f"{{{{{var_name}}}}}"
                            step["value"] = step["value"].replace(placeholder, str(var_value))

                    plan.append(step)

        # Set intents for POMBuilder compatibility
        state.context["intents"] = [
            {
                "intent": step["element"],
                "element": step["element"],
                "action": step["action"],
                "value": step["value"],
                "expected": step.get("expected")
            }
            for step in plan
        ]

        # Write to context["plan"] (state.plan is a read-only property that reads this)
        state.context["plan"] = plan
        return state

    # PHASE 1: Legacy raw_steps fallback
    raw_steps = state.context.get("raw_steps", [])
    if not raw_steps:
        raise ValueError("Planner requires context['suite'] (v2) or context['raw_steps'] (v1)")

    intents = parse_steps(raw_steps)
    state.context["intents"] = intents
    return state
