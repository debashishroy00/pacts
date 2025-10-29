import pytest
from pacts.backend.runtime import discovery

class FakeHandle:
    async def get_attribute(self, name):
        return {"id": "username", "name": "user"}.get(name)

class FakeLabelLocator:
    def __init__(self, text): self.text = text
    async def count(self): return 1
    @property
    def first(self): return self
    async def get_attribute(self, name): return "username" if name == "for" else None
    def locator(self, sel): return self
    async def element_handle(self): return FakeHandle()

class FakePlaceholderLocator:
    def __init__(self): pass
    async def count(self): return 1
    def nth(self, i): return self
    async def get_attribute(self, name):
        if name == "placeholder": return "Username"
        return None
    async def element_handle(self): return FakeHandle()

class FakePage:
    def get_by_text(self, pattern, exact=False): return FakeLabelLocator("Username")
    def locator(self, sel):
        if sel == "[placeholder]": return FakePlaceholderLocator()
        return FakeLabelLocator("Username")
    async def query_selector(self, sel): return object()

class FakeBrowser:
    def __init__(self): self.page = FakePage()
    async def find_by_label(self, pat): return ("#username", object())
    async def find_by_placeholder(self, pat): return ("#username", object())

@pytest.mark.asyncio
async def test_label_strategy():
    fb = FakeBrowser()
    out = await discovery._try_label(fb, {"element": "Username"})
    assert out and out["selector"] == "#username"
    assert out["meta"]["strategy"] == "label"

@pytest.mark.asyncio
async def test_placeholder_strategy():
    fb = FakeBrowser()
    out = await discovery._try_placeholder(fb, {"element": "Username"})
    assert out and out["selector"] == "#username"
    assert out["meta"]["strategy"] == "placeholder"
