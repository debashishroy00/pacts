import pytest
from pacts.backend.graph.state import RunState
from pacts.backend.agents.planner import run

@pytest.mark.asyncio
async def test_planner_parses_steps():
    state = RunState(req_id="REQ-1", context={
        "url": "https://example.com",
        "raw_steps": [
            "SearchInput@Header | fill | query",
            "SearchButton@Header | click"
        ]
    })
    out = await run(state)
    intents = out.context["intents"]
    assert intents[0]["action"] == "fill"
    assert intents[0]["region"] == "Header"
    assert intents[1]["action"] == "click"
