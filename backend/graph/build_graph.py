from __future__ import annotations
from langgraph.graph import StateGraph, END
from .state import RunState, Failure
from ..agents import planner


def executor_router(state: RunState) -> str:
    """
    Lazy discovery routing: decide what executor needs next.

    Returns:
        "human_wait" if current step requires human intervention (HITL)
        "pom_builder" if current step needs selector discovery
        "oracle_healer" if failure detected and healing attempts remain
        "verdict_rca" if done or max healing attempts reached
        "executor" if ready to execute next step
    """
    # Check if human intervention is required (HITL)
    if state.requires_human:
        print(f"[ROUTER] -> human_wait (HITL: manual intervention required)")
        return "human_wait"

    # Check if we've completed all steps
    if state.step_idx >= len(state.plan):
        print(f"[ROUTER] All steps complete ({state.step_idx}/{len(state.plan)}) -> verdict_rca")
        return "verdict_rca"

    # Check if current step needs selector discovery (lazy discovery)
    current_step = state.plan[state.step_idx]
    has_selector = bool(current_step.get("selector"))
    print(f"[ROUTER] Step {state.step_idx}/{len(state.plan)}: {current_step.get('element')} | selector={has_selector} | failure={state.failure}")

    if not has_selector:
        print(f"[ROUTER] -> pom_builder (no selector)")
        return "pom_builder"

    # If there's a failure, attempt healing (max 3 rounds)
    if state.failure != Failure.none:
        if state.heal_round < 3:
            print(f"[ROUTER] -> oracle_healer (heal_round={state.heal_round})")
            return "oracle_healer"
        else:
            # Max healing attempts reached, go to verdict
            print(f"[ROUTER] -> verdict_rca (max heals reached)")
            return "verdict_rca"

    # Ready to execute next step
    print(f"[ROUTER] -> executor (ready)")
    return "executor"


def build_graph():
    """
    Build the LangGraph state machine with LAZY DISCOVERY.

    Flow (Multi-Page Support):
    1. planner → parse Excel/JSON into full plan (no selectors yet)
    2. executor → check if current step has selector
       - NO selector → pom_builder (lazy discovery for current step only)
       - HAS selector → execute action
       - On navigation → wait for page load
    3. pom_builder → discover selector for CURRENT step only, return to executor
    4. Conditional routing from executor:
       - Need selector → pom_builder
       - Failure → oracle_healer (max 3 rounds)
       - Done → verdict_rca
       - Success → executor (next step)
    5. verdict_rca → generator → END
    """
    g = StateGraph(RunState)

    # Add agents
    g.add_node("planner", planner.run)

    from ..agents import pom_builder
    g.add_node("pom_builder", pom_builder.run)

    from ..agents import executor
    g.add_node("executor", executor.run)

    # OracleHealer v2 (real implementation)
    from ..agents import oracle_healer
    g.add_node("oracle_healer", oracle_healer.run)

    # VerdictRCA with MCP diagnostics (Phase 2)
    async def verdict_rca_stub(state: RunState) -> RunState:
        """
        Compute verdict based on execution results.
        Includes MCP Playwright diagnostics when available.
        """
        from ..mcp.playwright_client import get_client, USE_MCP
        import logging
        logger = logging.getLogger(__name__)

        if state.failure != Failure.none:
            state.verdict = "fail"
            rca = {
                "verdict": "fail",
                "step_idx": state.step_idx,
                "failure_type": state.failure.value,
                "heal_rounds": state.heal_round,
                "heal_events": state.heal_events
            }

            # Add MCP debug probe for failed selector (if available)
            if USE_MCP and state.step_idx < len(state.plan):
                failed_step = state.plan[state.step_idx]
                failed_selector = failed_step.get("selector")
                if failed_selector:
                    try:
                        mcp_client = get_client()
                        probe_result = await mcp_client.debug_probe(failed_selector)
                        if probe_result:
                            rca["mcp_probe"] = probe_result
                            logger.info(f"MCP debug probe attached to RCA for selector: {failed_selector}")
                    except Exception as e:
                        logger.warning(f"MCP debug_probe failed: {e}")

            state.context["rca"] = rca
            state.context["healed"] = state.heal_round > 0

        elif state.step_idx >= len(state.plan):
            state.verdict = "pass"
            state.context["rca"] = {
                "verdict": "pass",
                "steps_executed": state.step_idx,
                "total_steps": len(state.plan),
                "heal_rounds": state.heal_round,
                "message": "All steps executed successfully"
            }
            state.context["healed"] = state.heal_round > 0

        else:
            state.verdict = "partial"
            state.context["rca"] = {
                "verdict": "partial",
                "steps_executed": state.step_idx,
                "total_steps": len(state.plan),
                "heal_rounds": state.heal_round,
                "message": f"Completed {state.step_idx}/{len(state.plan)} steps"
            }
            state.context["healed"] = state.heal_round > 0

        return state

    g.add_node("verdict_rca", verdict_rca_stub)

    # Generator v2.0 (real implementation)
    from ..agents import generator
    g.add_node("generator", generator.run)

    # HITL (Human-in-the-Loop) wait node for manual intervention
    async def human_wait_node(state: RunState) -> RunState:
        """
        HITL node: Pause execution and wait for human intervention.
        Used for 2FA, CAPTCHA, or other manual verification steps.

        Non-TTY safe: Uses file/env signals instead of stdin input().
        """
        import logging
        import asyncio
        import os
        import time
        from pathlib import Path
        logger = logging.getLogger(__name__)

        # Ensure hitl/ directory exists
        hitl_dir = Path("hitl")
        hitl_dir.mkdir(exist_ok=True)

        # Clear old signal files
        continue_file = hitl_dir / "continue.ok"
        code_file = hitl_dir / "2fa_code.txt"
        if continue_file.exists():
            continue_file.unlink()
        if code_file.exists():
            code_file.unlink()

        current_step = state.plan[state.step_idx - 1] if state.step_idx > 0 else {}
        step_name = current_step.get("element", "Manual intervention")

        print(f"\n{'='*70}")
        print(f"⏸️  HUMAN INTERVENTION REQUIRED (HITL)")
        print(f"{'='*70}")
        print(f"Previous Step: {step_name}")
        print(f"\n📋 Instructions:")
        print(f"  1. Browser window is open - complete the manual action")
        print(f"  2. For 2FA: Enter code in browser, click Verify")
        print(f"\n🔄 To resume automation, choose ONE method:")
        print(f"  Method 1: Set environment variable PACTS_2FA_CODE=<code>")
        print(f"  Method 2: Create file hitl/2fa_code.txt with code")
        print(f"  Method 3: Create empty file hitl/continue.ok")
        print(f"\n⏱️  Waiting up to 15 minutes for signal...")
        print(f"{'='*70}\n")

        # Wait for signal (env var, file, or timeout)
        timeout_seconds = 900  # 15 minutes
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            # Check env var first (highest priority)
            code_from_env = os.getenv("PACTS_2FA_CODE")
            if code_from_env:
                print(f"[HITL] ✅ Got 2FA code from environment variable")
                state.human_input = code_from_env
                break

            # Check for code file
            if code_file.exists():
                code_text = code_file.read_text().strip()
                print(f"[HITL] ✅ Got 2FA code from hitl/2fa_code.txt")
                state.human_input = code_text
                code_file.unlink()  # Clean up
                break

            # Check for continue signal
            if continue_file.exists():
                print(f"[HITL] ✅ Got continue signal from hitl/continue.ok")
                state.human_input = "manual_complete"
                continue_file.unlink()  # Clean up
                break

            # Poll every 0.5 seconds
            await asyncio.sleep(0.5)

        else:
            # Timeout reached
            logger.warning(f"[HITL] ⏱️  Timeout reached ({timeout_seconds}s), continuing anyway...")
            state.human_input = "timeout"

        print(f"\n✅ Manual intervention completed, resuming automation...\n")

        # Reset HITL flag
        state.requires_human = False

        return state

    g.add_node("human_wait", human_wait_node)

    # NEW FLOW: Lazy discovery architecture
    g.set_entry_point("planner")
    g.add_edge("planner", "executor")  # Skip bulk discovery, go straight to executor

    # Executor uses lazy routing
    g.add_conditional_edges(
        "executor",
        executor_router,
        {
            "human_wait": "human_wait",  # Pause for human intervention (HITL)
            "pom_builder": "pom_builder",  # Need selector for current step
            "executor": "executor",  # Loop back to execute next step
            "oracle_healer": "oracle_healer",  # Heal on failure
            "verdict_rca": "verdict_rca",  # Finish and compute verdict
        }
    )

    # POMBuilder returns to executor after discovering selector
    g.add_edge("pom_builder", "executor")

    # After healing, go back to executor
    g.add_edge("oracle_healer", "executor")

    # After human intervention, return to executor to continue
    g.add_edge("human_wait", "executor")

    # After verdict, generate test artifact
    g.add_edge("verdict_rca", "generator")

    # After generation, end
    g.add_edge("generator", END)

    return g.compile()

async def ainvoke_graph(state: RunState) -> RunState:
    app = build_graph()
    # Increase recursion limit for multi-page flows (default: 25)
    return await app.ainvoke(state, config={"recursion_limit": 100})
