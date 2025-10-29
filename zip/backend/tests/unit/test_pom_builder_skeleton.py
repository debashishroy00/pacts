import pytest
import types

from pacts.backend.graph.state import RunState
from pacts.backend.agents.pom_builder import run as pom_run

class FakeBrowser:
    async def goto(self, url: str, wait: str = "domcontentloaded"):
        return None
    async def query(self, selector: str):
        return None
    async def locator_count(self, selector: str) -> int:
        return 1
    async def visible(self, el): return True
    async def enabled(self, el): return True
    async def bbox_stable(self, el, samples=3, delay_ms=120, tol=2.0): return True

class FakeManager:
    _client = FakeBrowser()
    @classmethod
    async def get(cls): return cls._client

# Monkeypatch BrowserManager.get inside the module under test
@pytest.mark.asyncio
async def test_pom_builder_produces_plan(monkeypatch):
    import pacts.backend.agents.pom_builder as mod
    async def fake_discover(browser, intent):
        return {"selector": "#fake", "score": 0.9, "meta": {"strategy": "stub"}}
    monkeypatch.setattr(mod, "BrowserManager", type("BM", (), {"get": FakeManager.get}))
    monkeypatch.setattr(mod, "discover_selector", fake_discover)

    state = RunState(req_id="REQ-1", context={
        "url": "https://example.com",
        "intents": [
            {"element": "SearchInput", "region": "Header", "action": "fill", "value": "q"},
            {"element": "SearchButton", "region": "Header", "action": "click"}
        ]
    })
    out = await pom_run(state)
    assert "plan" in out.context
    assert len(out.context["plan"]) == 2
    assert out.context["plan"][0]["selector"] == "#fake"
