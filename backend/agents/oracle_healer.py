"""
OracleHealer v2 Agent - Autonomous Self-Healing

Implements reveal, reprobe, and stability-wait strategies to recover from failures.
Max 3 healing rounds before routing to VerdictRCA.
"""
from __future__ import annotations
import time
from ..graph.state import RunState, Failure
from ..runtime.browser_manager import BrowserManager
from ..runtime.discovery import reprobe_with_alternates
from ..runtime.policies import five_point_gate
from ..telemetry.tracing import traced


@traced("oracle_healer")
async def run(state: RunState) -> RunState:
    """
    OracleHealer v2: Autonomous healing for failed selectors/actions.

    Healing Playbook:
        1. REVEAL: Scroll into view, dismiss overlays, ensure focus
        2. REPROBE: Re-run discovery with alternate strategies
        3. STABILITY: Wait for animations/network idle, re-check gate
        4. ADAPTIVE RETRY: Increment timeouts per heal round

    Args:
        state: RunState with failure information

    Returns:
        RunState with healed selector or failure state for VerdictRCA
    """
    # Guard: Max healing rounds
    if state.heal_round >= 3:
        return state  # Let routing send to verdict_rca

    # Get browser singleton
    browser = await BrowserManager.get()

    # Increment heal round
    state.heal_round += 1
    heal_start_ms = int(time.time() * 1000)

    # Get failed step
    if state.step_idx >= len(state.plan):
        # No plan to heal
        return state

    step = state.plan[state.step_idx]
    selector = step.get("selector")
    intent = {
        "element": step.get("element"),
        "action": step.get("action"),
        "value": step.get("value"),
        "region": step.get("region"),
    }

    # Track heal event metadata
    heal_event = {
        "round": state.heal_round,
        "step_idx": state.step_idx,
        "failure_type": state.failure.value,
        "original_selector": selector,
        "actions": [],
    }

    # ==========================================
    # STEP 1: REVEAL
    # ==========================================
    reveal_actions = []

    # Bring page to front
    if await browser.bring_to_front():
        reveal_actions.append("bring_to_front")

    # Scroll into view
    if selector and await browser.scroll_into_view(selector):
        reveal_actions.append("scroll_into_view")

    # Incremental scroll (for lazy-loading UIs)
    if await browser.incremental_scroll(200):
        reveal_actions.append("incremental_scroll")

    # Dismiss overlays (modals, popups)
    dismissed_count = await browser.dismiss_overlays()
    if dismissed_count > 0:
        reveal_actions.append(f"dismiss_overlays({dismissed_count})")

    # Wait for network idle
    if await browser.wait_network_idle(1000):
        reveal_actions.append("network_idle")

    heal_event["actions"].extend(reveal_actions)

    # ==========================================
    # STEP 2: REPROBE (if original selector failed)
    # ==========================================
    new_selector = None
    reprobe_strategy = None

    if state.failure in [Failure.timeout, Failure.not_unique]:
        # Re-discover with alternate strategies
        hints = state.context.get("hints", {})
        discovered = await reprobe_with_alternates(
            browser,
            intent,
            heal_round=state.heal_round,
            hints=hints
        )

        if discovered:
            new_selector = discovered["selector"]
            reprobe_strategy = discovered["meta"]["strategy"]
            heal_event["actions"].append(f"reprobe:{reprobe_strategy}")
            heal_event["new_selector"] = new_selector

            # Update plan with new selector
            state.plan[state.step_idx]["selector"] = new_selector
            selector = new_selector

    # ==========================================
    # STEP 3: STABILITY & GATE VALIDATION
    # ==========================================
    gate_ok = False

    if selector:
        # Wait for stability (animations, transitions)
        stability_ok = await browser.wait_for_stability(
            selector,
            samples=3 + state.heal_round,
            delay_ms=200,
            tol=2.0 + (0.5 * state.heal_round)
        )
        if stability_ok:
            heal_event["actions"].append("stability_wait")

        # Re-validate with five-point gate (healing-friendly policies)
        try:
            el = await browser.query(selector)
            if el:
                gates = await five_point_gate(
                    browser,
                    selector,
                    el,
                    heal_round=state.heal_round,
                    stabilize=True,
                    samples=3 + state.heal_round,
                    timeout_ms=2000 + (1000 * state.heal_round)
                )
                gate_ok = all(gates.values())
                heal_event["gate_result"] = gates
        except Exception as e:
            heal_event["gate_error"] = str(e)

    # ==========================================
    # FINALIZE HEAL EVENT
    # ==========================================
    heal_end_ms = int(time.time() * 1000)
    heal_event["duration_ms"] = heal_end_ms - heal_start_ms
    heal_event["success"] = gate_ok

    # CRITICAL: Ensure heal_events list exists before appending
    if not hasattr(state, "heal_events") or state.heal_events is None:
        state.heal_events = []
    state.heal_events.append(heal_event)

    # Reset failure if healing succeeded
    if gate_ok:
        state.failure = Failure.none
        state.last_selector = selector
    # else: keep failure set, routing will send to verdict_rca or retry

    return state
