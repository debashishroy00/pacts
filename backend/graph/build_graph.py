from __future__ import annotations
from langgraph.graph import StateGraph, END
from .state import RunState, Failure
from ..agents import planner

def build_graph():
    g = StateGraph(RunState)
    g.add_node("planner", planner.run)
    from ..agents import pom_builder
    g.add_node("pom_builder", pom_builder.run)
    g.set_entry_point("planner")
    g.add_edge("planner", "pom_builder")
    g.add_edge("pom_builder", END)
    return g.compile()

async def ainvoke_graph(state: RunState) -> RunState:
    app = build_graph()
    return await app.ainvoke(state)
