from __future__ import annotations
from langgraph.graph import StateGraph, END
from .state import RunState, Failure
from ..agents import planner


def should_heal(state: RunState) -> str:
    """
    Routing function: decide whether to heal or finish.

    Returns:
        "oracle_healer" if failure detected and healing attempts remain
        "verdict_rca" if max healing attempts reached or success
        END if all steps completed successfully
    """
    # If we've completed all steps successfully, go to verdict
    if state.step_idx >= len(state.plan) and state.failure == Failure.none:
        return "verdict_rca"

    # If there's a failure, attempt healing (max 3 rounds)
    if state.failure != Failure.none:
        if state.heal_round < 3:
            return "oracle_healer"
        else:
            # Max healing attempts reached, go to verdict
            return "verdict_rca"

    # Continue executing
    return "executor"


def build_graph():
    """
    Build the LangGraph state machine.

    Flow:
    1. planner → parse Excel requirements into intents
    2. pom_builder → discover and verify selectors
    3. executor → execute actions with five_point_gate validation
    4. Conditional routing:
       - If failure → oracle_healer (max 3 rounds)
       - If success or max heals → verdict_rca
       - If more steps → executor (loop)
    5. verdict_rca → compute verdict, RCA, metrics

    Note: oracle_healer and verdict_rca are stubs for Phase 1.
    """
    g = StateGraph(RunState)

    # Add agents
    g.add_node("planner", planner.run)

    from ..agents import pom_builder
    g.add_node("pom_builder", pom_builder.run)

    from ..agents import executor
    g.add_node("executor", executor.run)

    # Stubs for Phase 1 (to be implemented later)
    async def oracle_healer_stub(state: RunState) -> RunState:
        """Stub: increment heal_round and retry executor."""
        state.heal_round += 1
        state.failure = Failure.none  # Reset failure to retry
        return state

    async def verdict_rca_stub(state: RunState) -> RunState:
        """Stub: compute verdict based on execution results."""
        if state.failure != Failure.none:
            state.verdict = "fail"
            state.context["rca"] = f"Failed at step {state.step_idx} with {state.failure.value}"
        elif state.step_idx >= len(state.plan):
            state.verdict = "pass"
            state.context["rca"] = "All steps executed successfully"
        else:
            state.verdict = "partial"
            state.context["rca"] = f"Completed {state.step_idx}/{len(state.plan)} steps"
        return state

    g.add_node("oracle_healer", oracle_healer_stub)
    g.add_node("verdict_rca", verdict_rca_stub)

    # Define edges
    g.set_entry_point("planner")
    g.add_edge("planner", "pom_builder")
    g.add_edge("pom_builder", "executor")

    # Conditional routing from executor
    g.add_conditional_edges(
        "executor",
        should_heal,
        {
            "executor": "executor",  # Loop back to execute next step
            "oracle_healer": "oracle_healer",  # Heal on failure
            "verdict_rca": "verdict_rca",  # Finish and compute verdict
        }
    )

    # After healing, go back to executor
    g.add_edge("oracle_healer", "executor")

    # After verdict, end
    g.add_edge("verdict_rca", END)

    return g.compile()

async def ainvoke_graph(state: RunState) -> RunState:
    app = build_graph()
    return await app.ainvoke(state)
