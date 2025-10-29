from __future__ import annotations
from typing import Optional
# NOTE: Actual Playwright import deferred to runtime env to keep tests light.
# from playwright.async_api import async_playwright, Page, ElementHandle

class BrowserClient:
    def __init__(self):
        self._pw = None
        self.browser = None
        self.page = None  # type: ignore

    async def start(self, headless: bool = True, project: str = "chromium"):
        # Lazy import to avoid env dependency during unit tests
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        if project == "chromium":
            self.browser = await self._pw.chromium.launch(headless=headless)
        elif project == "firefox":
            self.browser = await self._pw.firefox.launch(headless=headless)
        else:
            self.browser = await self._pw.webkit.launch(headless=headless)
        self.page = await self.browser.new_page()

    async def goto(self, url: str, wait: str = "domcontentloaded"):
        assert self.page, "Call start() first"
        await self.page.goto(url, wait_until=wait)

    async def query(self, selector: str):
        assert self.page, "Call start() first"
        return await self.page.query_selector(selector)

    async def locator_count(self, selector: str) -> int:
        assert self.page, "Call start() first"
        return await self.page.locator(selector).count()

    async def visible(self, el) -> bool:
        return await el.is_visible()

    async def enabled(self, el) -> bool:
        return await el.is_enabled()

    async def bbox_stable(self, el, samples: int = 3, delay_ms: int = 120, tol: float = 2.0) -> bool:
        assert self.page, "Call start() first"
        boxes = []
        for _ in range(samples):
            box = await el.bounding_box()
            if not box:
                return False
            boxes.append(box)
            await self.page.wait_for_timeout(delay_ms)
        keys = ["x", "y", "width", "height"]
        return all(abs(boxes[i][k] - boxes[0][k]) <= tol for i in range(1, len(boxes)) for k in keys)

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self._pw:
            await self._pw.stop()
