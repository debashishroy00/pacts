from __future__ import annotations
from typing import Dict, Any, List
from ..graph.state import RunState
from ..runtime.browser_manager import BrowserManager
from ..runtime.discovery import discover_selector
from ..telemetry.tracing import traced

@traced("pom_builder")
async def run(state: RunState) -> RunState:
    browser = await BrowserManager.get()
    url = state.context.get("url")
    if not url:
        raise ValueError("POMBuilder requires context['url']")
    await browser.goto(url)

    plan: List[Dict[str, Any]] = []
    for step in state.context.get("intents", []):
        cand = await discover_selector(browser, step)
        if cand:
            plan.append({
                **step,
                "selector": cand["selector"],
                "meta": cand.get("meta", {}),
                "confidence": cand.get("score", 0.0)
            })
    state.context["plan"] = plan
    return state
