from __future__ import annotations
import pytest
from backend.graph.state import RunState, Failure
from backend.agents import executor


class FakeElement:
    """Fake element handle for testing."""
    def __init__(self, visible=True, enabled=True, stable=True):
        self._visible = visible
        self._enabled = enabled
        self._stable = stable

    async def is_visible(self):
        return self._visible

    async def is_enabled(self):
        return self._enabled

    async def bounding_box(self):
        if self._stable:
            return {"x": 100, "y": 200, "width": 150, "height": 40}
        return None


class FakeLocator:
    """Fake Playwright locator."""
    def __init__(self, success=True, action_error=False):
        self.success = success
        self.action_error = action_error

    async def click(self, timeout=5000):
        if self.action_error:
            raise Exception("Click failed")

    async def fill(self, value, timeout=5000):
        if self.action_error:
            raise Exception("Fill failed")

    async def type(self, value, delay=50, timeout=5000):
        if self.action_error:
            raise Exception("Type failed")

    async def press(self, value, timeout=5000):
        if self.action_error:
            raise Exception("Press failed")

    async def select_option(self, value, timeout=5000):
        if self.action_error:
            raise Exception("Select failed")

    async def check(self, timeout=5000):
        if self.action_error:
            raise Exception("Check failed")

    async def uncheck(self, timeout=5000):
        if self.action_error:
            raise Exception("Uncheck failed")

    async def hover(self, timeout=5000):
        if self.action_error:
            raise Exception("Hover failed")

    async def focus(self, timeout=5000):
        if self.action_error:
            raise Exception("Focus failed")


class FakePage:
    """Fake Playwright page."""
    def __init__(self, action_error=False):
        self.action_error = action_error

    def locator(self, selector):
        return FakeLocator(action_error=self.action_error)

    async def wait_for_timeout(self, ms):
        pass


class FakeBrowser:
    """Fake browser for testing."""
    def __init__(self, element=None, count=1, action_error=False):
        self.element = element or FakeElement()
        self.count = count
        self.page = FakePage(action_error=action_error)

    async def query(self, selector):
        return self.element

    async def locator_count(self, selector):
        return self.count

    async def visible(self, el):
        return await el.is_visible()

    async def enabled(self, el):
        return await el.is_enabled()

    async def bbox_stable(self, el, samples=3, delay_ms=120, tol=2.0):
        boxes = []
        for _ in range(samples):
            box = await el.bounding_box()
            if not box:
                return False
            boxes.append(box)
        return True


@pytest.mark.asyncio
async def test_executor_successful_click(monkeypatch):
    """Test executor successfully executes a click action."""
    fake_browser = FakeBrowser()

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-001",
        step_idx=0,
        context={
            "plan": [
                {
                    "selector": "#login-button",
                    "action": "click",
                    "element": "Login",
                }
            ]
        }
    )

    result = await executor.run(state)

    assert result.step_idx == 1  # Moved to next step
    assert result.failure == Failure.none
    assert result.last_selector == "#login-button"
    assert "executed_steps" in result.context
    assert len(result.context["executed_steps"]) == 1


@pytest.mark.asyncio
async def test_executor_successful_fill(monkeypatch):
    """Test executor successfully executes a fill action."""
    fake_browser = FakeBrowser()

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-002",
        step_idx=0,
        context={
            "plan": [
                {
                    "selector": "#username",
                    "action": "fill",
                    "value": "testuser",
                    "element": "Username",
                }
            ]
        }
    )

    result = await executor.run(state)

    assert result.step_idx == 1
    assert result.failure == Failure.none
    assert result.last_selector == "#username"


@pytest.mark.asyncio
async def test_executor_not_unique_failure(monkeypatch):
    """Test executor detects non-unique selector."""
    fake_browser = FakeBrowser(count=2)  # Multiple elements found

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-003",
        step_idx=0,
        context={
            "plan": [
                {
                    "selector": ".button",  # Non-unique selector
                    "action": "click",
                }
            ]
        }
    )

    result = await executor.run(state)

    assert result.step_idx == 0  # Did not advance
    assert result.failure == Failure.not_unique
    assert result.last_selector == ".button"


@pytest.mark.asyncio
async def test_executor_not_visible_failure(monkeypatch):
    """Test executor detects invisible element."""
    fake_element = FakeElement(visible=False)
    fake_browser = FakeBrowser(element=fake_element)

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-004",
        step_idx=0,
        context={
            "plan": [
                {
                    "selector": "#hidden-button",
                    "action": "click",
                }
            ]
        }
    )

    result = await executor.run(state)

    assert result.step_idx == 0
    assert result.failure == Failure.not_visible


@pytest.mark.asyncio
async def test_executor_disabled_failure(monkeypatch):
    """Test executor detects disabled element."""
    fake_element = FakeElement(enabled=False)
    fake_browser = FakeBrowser(element=fake_element)

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-005",
        step_idx=0,
        context={
            "plan": [
                {
                    "selector": "#disabled-button",
                    "action": "click",
                }
            ]
        }
    )

    result = await executor.run(state)

    assert result.step_idx == 0
    assert result.failure == Failure.disabled


@pytest.mark.asyncio
async def test_executor_unstable_failure(monkeypatch):
    """Test executor detects unstable element (bbox changing)."""
    fake_element = FakeElement(stable=False)
    fake_browser = FakeBrowser(element=fake_element)

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-006",
        step_idx=0,
        context={
            "plan": [
                {
                    "selector": "#animating-button",
                    "action": "click",
                }
            ]
        }
    )

    result = await executor.run(state)

    assert result.step_idx == 0
    assert result.failure == Failure.unstable


@pytest.mark.asyncio
async def test_executor_action_timeout(monkeypatch):
    """Test executor handles action timeout/error."""
    fake_browser = FakeBrowser(action_error=True)

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-007",
        step_idx=0,
        context={
            "plan": [
                {
                    "selector": "#broken-button",
                    "action": "click",
                }
            ]
        }
    )

    result = await executor.run(state)

    assert result.step_idx == 0
    assert result.failure == Failure.timeout


@pytest.mark.asyncio
async def test_executor_multiple_steps(monkeypatch):
    """Test executor processes multiple steps sequentially."""
    fake_browser = FakeBrowser()

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-008",
        step_idx=0,
        context={
            "plan": [
                {"selector": "#username", "action": "fill", "value": "user"},
                {"selector": "#password", "action": "fill", "value": "pass"},
                {"selector": "#login", "action": "click"},
            ]
        }
    )

    # Execute first step
    result = await executor.run(state)
    assert result.step_idx == 1
    assert result.failure == Failure.none

    # Execute second step
    result = await executor.run(result)
    assert result.step_idx == 2
    assert result.failure == Failure.none

    # Execute third step
    result = await executor.run(result)
    assert result.step_idx == 3
    assert result.failure == Failure.none


@pytest.mark.asyncio
async def test_executor_all_steps_completed(monkeypatch):
    """Test executor sets verdict=pass when all steps completed."""
    fake_browser = FakeBrowser()

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-009",
        step_idx=2,  # Already completed 2 steps
        context={
            "plan": [
                {"selector": "#step1", "action": "click"},
                {"selector": "#step2", "action": "click"},
            ]
        }
    )

    result = await executor.run(state)

    assert result.verdict == "pass"


@pytest.mark.asyncio
async def test_executor_no_plan(monkeypatch):
    """Test executor handles missing plan gracefully."""
    fake_browser = FakeBrowser()

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(req_id="REQ-010", context={})

    result = await executor.run(state)

    assert result.verdict == "fail"
    assert "error" in result.context
    assert "No plan" in result.context["error"]


@pytest.mark.asyncio
async def test_executor_tracks_executed_steps(monkeypatch):
    """Test executor tracks execution history in context."""
    fake_browser = FakeBrowser()

    async def mock_get():
        return fake_browser

    from backend.runtime import browser_manager
    monkeypatch.setattr(browser_manager.BrowserManager, "get", mock_get)

    state = RunState(
        req_id="REQ-011",
        step_idx=0,
        heal_round=2,  # Simulate healing rounds
        context={
            "plan": [
                {"selector": "#button", "action": "click", "value": None}
            ]
        }
    )

    result = await executor.run(state)

    assert "executed_steps" in result.context
    executed = result.context["executed_steps"][0]
    assert executed["step_idx"] == 0
    assert executed["selector"] == "#button"
    assert executed["action"] == "click"
    assert executed["heal_round"] == 2  # Tracks which heal round this was
