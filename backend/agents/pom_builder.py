from __future__ import annotations
from typing import Dict, Any, List
from ..graph.state import RunState, Failure
from ..runtime.browser_manager import BrowserManager
from ..runtime.discovery import discover_selector
from ..telemetry.tracing import traced

@traced("pom_builder")
async def run(state: RunState) -> RunState:
    """
    POMBuilder with LAZY DISCOVERY support.

    Mode 1 (Lazy - Single-Step Discovery):
        If state.plan exists with steps, discover selector for CURRENT step only (state.step_idx).
        Enables multi-page flows where elements appear after navigation.

    Mode 2 (Legacy - Bulk Discovery):
        If state.plan is empty, discover selectors for all intents at once.
        Used for simple single-page tests (backward compatibility).
    """
    # Pass browser config from context (for headed mode, slow_mo, etc.)
    browser_config = state.context.get("browser_config", {})
    browser = await BrowserManager.get(config=browser_config)

    # Lazy mode: discover selector for current step only
    if state.plan and state.step_idx < len(state.plan):
        # Ensure browser is navigated to initial URL (if first time or blank page)
        url = state.context.get("url")
        if url:
            current_url = browser.page.url if browser.page else ""
            if not current_url or "about:blank" in current_url:
                print(f"[POMBuilder] Navigating to {url}")
                await browser.goto(url)

        current_step = state.plan[state.step_idx]
        print(f"[POMBuilder] Discovering selector for step {state.step_idx}: {current_step.get('element')}")

        # Discover selector for this step
        intent = {
            "element": current_step.get("element"),
            "action": current_step.get("action"),
            "value": current_step.get("value")
        }

        cand = await discover_selector(browser, intent)
        print(f"[POMBuilder] Discovery result: {cand}")
        if cand:
            # Update ONLY the current step in the plan
            updated_step = {
                **current_step,
                "selector": cand["selector"],
                "meta": cand.get("meta", {}),
                "confidence": cand.get("score", 0.0)
            }

            # Write back to context["plan"] (state.plan is read-only property)
            plan_copy = list(state.plan)
            plan_copy[state.step_idx] = updated_step
            state.context["plan"] = plan_copy

            # Clear any pre-existing failure (fresh discovery means ready to execute)
            state.failure = Failure.none
        else:
            # Discovery failed - mark as timeout
            state.failure = Failure.timeout

        return state

    # Legacy mode: bulk discovery (for initial page or backward compatibility)
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

    # Write to context["plan"] (state.plan is a read-only property that reads this)
    state.context["plan"] = plan
    return state
