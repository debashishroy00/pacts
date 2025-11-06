"""
OracleHealer v2 Agent - Autonomous Self-Healing

Implements reveal, reprobe, and stability-wait strategies to recover from failures.
Max healing rounds configurable via MAX_HEAL_ROUNDS env (default: 3).

Integrates with MCP Playwright for advanced reveal/reprobe capabilities when available.
"""
from __future__ import annotations
import time
import logging
import os
from ..graph.state import RunState, Failure
from ..runtime.browser_manager import BrowserManager
from ..runtime.discovery import reprobe_with_alternates
from ..runtime.policies import five_point_gate
from ..telemetry.tracing import traced
from ..mcp.playwright_client import get_client, USE_MCP

logger = logging.getLogger(__name__)


@traced("oracle_healer")
async def run(state: RunState) -> RunState:
    """
    OracleHealer v2: Autonomous healing for failed selectors/actions.

    Healing Playbook:
        1. REVEAL: Scroll into view, dismiss overlays, ensure focus
        2. REPROBE: Re-run discovery with alternate strategies (history-aware)
        3. STABILITY: Wait for animations/network idle, re-check gate
        4. ADAPTIVE RETRY: Increment timeouts per heal round

    History Integration (Day 11):
        - Query HealHistory for best strategies before attempting healing
        - Try learned strategies first, fall back to default list
        - Record outcome after each heal attempt for learning

    Args:
        state: RunState with failure information

    Returns:
        RunState with healed selector or failure state for VerdictRCA
    """
    # Guard: Max healing rounds (from env)
    max_heal_rounds = int(os.getenv("MAX_HEAL_ROUNDS", "3"))
    if state.heal_round >= max_heal_rounds:
        return state  # Let routing send to verdict_rca

    # Get browser singleton (pass config for headed mode, slow_mo, etc.)
    browser_config = state.context.get("browser_config", {})
    browser = await BrowserManager.get(config=browser_config)

    # Get storage for HealHistory (Day 11 integration)
    from ..storage.init import get_storage
    storage = await get_storage()
    heal_history = storage.heal_history if storage else None

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

    # PRIORITY: MCP Playwright reveal (if enabled)
    if USE_MCP:
        try:
            mcp_client = get_client()
            mcp_reveal = await mcp_client.reveal(step)
            if mcp_reveal and mcp_reveal.get("success"):
                mcp_actions = mcp_reveal.get("actions", [])
                reveal_actions.extend([f"mcp_{action}" for action in mcp_actions])
                logger.info(f"MCP reveal actions for step {state.step_idx}: {mcp_actions}")
        except Exception as e:
            logger.warning(f"MCP reveal failed, falling back to local: {e}")
            # Fall through to local reveal

    # FALLBACK: Local reveal actions
    if not reveal_actions:  # Only run local if MCP didn't handle it
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
    # STEP 2: REPROBE (if original selector failed) - HISTORY-AWARE
    # ==========================================
    new_selector = None
    reprobe_strategy = None

    # Check if navigation occurred - if so, don't reprobe (old selector is on old page)
    navigation_occurred = state.context.get("navigation_occurred", False)
    navigation_step = state.context.get("navigation_step", -1)

    if navigation_occurred and navigation_step == state.step_idx:
        # Navigation just happened - the element is gone because we're on a new page
        # This is SUCCESS, not a failure. Mark step as complete and move on.
        print(f"[OracleHealer] Navigation detected - step succeeded, no reprobe needed")
        state.failure = Failure.none
        state.step_idx += 1
        state.context["navigation_occurred"] = False  # Clear flag
        heal_event["actions"].append("navigation_success")
        state.heal_events.append(heal_event)
        return state

    if state.failure in [Failure.timeout, Failure.not_unique]:
        # Get best strategies from HealHistory (Day 11 integration)
        best_strategies = []
        if heal_history:
            url = state.context.get("url", "")
            element = intent.get("element", "")
            try:
                best_strategies = await heal_history.get_best_strategy(
                    element=element,
                    url=url,
                    top_n=3
                )
                if best_strategies:
                    strategy_names = [s["strategy"] for s in best_strategies]
                    logger.info(f"[HEAL] 🎯 Learned strategies for {element}: {strategy_names}")
                    heal_event["learned_strategies"] = strategy_names
            except Exception as e:
                logger.warning(f"[HEAL] HealHistory query failed, using defaults: {e}")

        # Re-discover with alternate strategies (prioritize learned strategies)
        hints = state.context.get("hints", {})
        if best_strategies:
            # Add learned strategies to hints (reprobe will try these first)
            hints["preferred_strategies"] = [s["strategy"] for s in best_strategies]

        discovered = await reprobe_with_alternates(
            browser,
            intent,
            heal_round=state.heal_round,
            hints=hints
        )

        if discovered:
            # Week 4: Prefer stable selectors (label-first strategy)
            # If multiple candidates exist (future: reprobe could return list), sort by stability
            candidates = [discovered["selector"]]  # Could have multiple from reprobe
            stable_first = sorted(
                candidates,
                key=lambda s: 0 if any(k in s for k in ('[aria-label=', '[name=', '[placeholder=')) else 1
            )
            new_selector = stable_first[0]

            # Week 5: Detect no-progress loop (same selector returned)
            if new_selector == selector:
                print(f"[HEAL] ⚠️ No progress: new selector identical to old ({new_selector[:60]})")
                heal_event["actions"].append("no_progress_same_selector")
                # Continue anyway to consume heal round and eventually hit max limit

            reprobe_strategy = discovered["meta"]["strategy"]
            heal_event["actions"].append(f"reprobe:{reprobe_strategy}")
            heal_event["new_selector"] = new_selector

            # Update plan with new selector
            state.plan[state.step_idx]["selector"] = new_selector
            selector = new_selector
        else:
            # Week 3 Patch: Discovery returned None - prevent infinite loop
            print(f"[HEAL] ⚠️ Discovery returned None for '{intent.get('element')}' (round {state.heal_round})")
            heal_event["actions"].append("discovery_none")
            selector = None  # Ensure selector is cleared to fail fast

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

    # ==========================================
    # RECORD OUTCOME TO HEALHISTORY (Day 11)
    # ==========================================
    if heal_history and reprobe_strategy:
        # Record healing outcome for learning
        url = state.context.get("url", "")
        element = intent.get("element", "")
        try:
            await heal_history.record_outcome(
                element=element,
                url=url,
                strategy=reprobe_strategy,
                success=gate_ok,
                heal_time_ms=heal_event["duration_ms"]
            )
            logger.info(f"[HEAL] 📊 Recorded outcome: {reprobe_strategy} → {'✅' if gate_ok else '❌'}")
        except Exception as e:
            logger.warning(f"[HEAL] Failed to record outcome: {e}")

    # Reset failure if healing succeeded
    if gate_ok:
        state.failure = Failure.none
        state.last_selector = selector
    # else: keep failure set, routing will send to verdict_rca or retry

    return state
