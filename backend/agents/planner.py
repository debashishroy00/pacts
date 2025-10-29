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
    raw_steps = state.context.get("raw_steps", [])
    if not raw_steps:
        raise ValueError("Planner requires context['raw_steps']")
    state.context["intents"] = parse_steps(raw_steps)
    return state
