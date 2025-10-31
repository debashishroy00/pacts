from __future__ import annotations
from typing import Dict, Any, Optional
from ..graph.state import RunState, Failure
from ..runtime.browser_manager import BrowserManager
from ..runtime.policies import five_point_gate
from ..telemetry.tracing import traced


async def _perform_action(browser, action: str, selector: str, value: Optional[str] = None) -> bool:
    """
    Execute a single action on an element.

    Returns:
        bool: True if action succeeded, False otherwise
    """
    try:
        locator = browser.page.locator(selector)

        if action == "click":
            await locator.click(timeout=5000)
            return True

        elif action == "fill":
            if value is None:
                return False
            await locator.fill(value, timeout=5000)
            return True

        elif action == "type":
            if value is None:
                return False
            await locator.type(value, delay=50, timeout=5000)
            return True

        elif action == "press":
            if value is None:
                return False
            await locator.press(value, timeout=5000)
            return True

        elif action == "select":
            if value is None:
                return False
            await locator.select_option(value, timeout=5000)
            return True

        elif action == "check":
            await locator.check(timeout=5000)
            return True

        elif action == "uncheck":
            await locator.uncheck(timeout=5000)
            return True

        elif action == "hover":
            await locator.hover(timeout=5000)
            return True

        elif action == "focus":
            await locator.focus(timeout=5000)
            return True

        else:
            # Unknown action
            return False

    except Exception as e:
        # Log the error but return False to trigger healing
        return False


async def _validate_step(browser, step: Dict[str, Any], heal_round: int = 0) -> tuple[Optional[Failure], Optional[Any]]:
    """
    Validate a step using the five_point_gate.

    Args:
        browser: BrowserClient instance
        step: Step dict with selector, action, value
        heal_round: Current healing round (for adaptive timeouts/tolerance)

    Returns:
        tuple: (Failure enum if failed, element handle if succeeded)
    """
    selector = step.get("selector")
    if not selector:
        return Failure.timeout, None

    # Query the element
    el = await browser.query(selector)
    if not el:
        return Failure.timeout, None

    # Run five-point gate with healing-aware policies
    gates = await five_point_gate(
        browser,
        selector,
        el,
        heal_round=heal_round,
        stabilize=False,  # Executor doesn't pre-stabilize (OracleHealer does)
        samples=3,
        timeout_ms=2000
    )

    # Check each gate and return appropriate failure
    if not gates["unique"]:
        return Failure.not_unique, None
    if not gates["visible"]:
        return Failure.not_visible, None
    if not gates["enabled"]:
        return Failure.disabled, None
    if not gates["stable_bbox"]:
        return Failure.unstable, None
    # scoped is always True for now (future: frame/shadow DOM)

    return None, el


@traced("executor")
async def run(state: RunState) -> RunState:
    """
    Executor Agent: Execute actions from the verified plan.

    Process:
    1. Get current step from plan using step_idx
    2. Validate element with five_point_gate
    3. Perform the action (click, fill, etc.)
    4. Update step_idx or set failure state

    State updates:
    - step_idx: incremented on success
    - failure: set to appropriate Failure enum on validation/action failure
    - last_selector: updated to current selector
    - context["executed_steps"]: list of successfully executed steps
    """
    browser = await BrowserManager.get()

    plan = state.plan
    if not plan:
        # No plan to execute
        state.verdict = "fail"
        state.context["error"] = "Executor: No plan available"
        return state

    # Check if we've completed all steps
    if state.step_idx >= len(plan):
        # All steps executed successfully
        state.verdict = "pass"
        return state

    # Get current step
    step = plan[state.step_idx]
    selector = step.get("selector")
    action = step.get("action", "click")
    value = step.get("value")

    # Update last_selector for healing
    state.last_selector = selector

    # Validate element with five_point gate (pass heal_round for adaptive policies)
    failure, el = await _validate_step(browser, step, heal_round=state.heal_round)

    if failure:
        # Validation failed - set failure state for healing
        state.failure = failure
        return state

    # Perform the action
    success = await _perform_action(browser, action, selector, value)

    if not success:
        # Action failed - mark as timeout for healing
        state.failure = Failure.timeout
        return state

    # Success! Update state
    state.failure = Failure.none
    state.step_idx += 1

    # Track executed steps in context
    if "executed_steps" not in state.context:
        state.context["executed_steps"] = []
    state.context["executed_steps"].append({
        "step_idx": state.step_idx - 1,
        "selector": selector,
        "action": action,
        "value": value,
        "heal_round": state.heal_round
    })

    return state
