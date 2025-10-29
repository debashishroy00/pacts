import pytest
import re
from backend.runtime import discovery

class FakeLocator:
    async def count(self): return 1
    async def element_handle(self): return FakeHandle()

class FakeHandle:
    async def get_attribute(self, name):
        if name == "id": return "login-button"
        return None

class FakePage:
    def get_by_role(self, role, name):
        # Pretend we always find the element
        pattern = name if hasattr(name, 'pattern') else str(name)
        return FakeLocator()

class FakeBrowser:
    def __init__(self): self.page = FakePage()
    async def find_by_role(self, role, pat): return ("#login-button", object())

@pytest.mark.asyncio
async def test_role_name_strategy_discovers_button():
    fb = FakeBrowser()
    intent = {"element": "Login", "action": "click"}
    out = await discovery._try_role_name(fb, intent)
    assert out is not None
    assert out["meta"]["strategy"] == "role_name"
    assert out["meta"]["role"] == "button"
    assert out["selector"] == "#login-button"
