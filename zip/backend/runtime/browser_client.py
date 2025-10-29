from __future__ import annotations
from typing import Optional, Tuple, Any

class BrowserClient:
    def __init__(self):
        self._pw = None
        self.browser = None
        self.page = None  # type: ignore

    async def start(self, headless: bool = True, project: str = "chromium"):
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

    # --- Existing helpers (label/placeholder) omitted for brevity ---
    async def find_by_label(self, text_pattern: Any):
        assert self.page, "Call start() first"
        lab = self.page.get_by_text(text_pattern, exact=False).locator('xpath=ancestor-or-self::label[1]')
        count = await lab.count()
        if count == 0:
            lab = self.page.locator('label').filter(has_text=text_pattern)
            count = await lab.count()
            if count == 0:
                return None
        label = lab.first
        for_attr = await label.get_attribute('for')
        if for_attr:
            sel = f"#{for_attr}"
            el = await self.page.query_selector(sel)
            if el:
                return sel, el
        inner = label.locator('input, textarea, [role="textbox"]')
        if await inner.count() > 0:
            handle = await inner.first.element_handle()
            if handle:
                idv = await handle.get_attribute('id')
                if idv:
                    return f"#{idv}", handle
                namev = await handle.get_attribute('name')
                if namev:
                    return f"[name="{namev}"]", handle
                return 'xpath=.', handle
        return None

    async def find_by_placeholder(self, text_pattern: Any):
        assert self.page, "Call start() first"
        loc = self.page.locator('[placeholder]')
        count = await loc.count()
        if count == 0:
            return None
        limit = min(count, 50)
        for i in range(limit):
            item = loc.nth(i)
            ph = await item.get_attribute('placeholder')
            if not ph:
                continue
            try:
                if hasattr(text_pattern, 'search'):
                    ok = bool(text_pattern.search(ph))
                else:
                    ok = str(text_pattern).lower() in ph.lower()
            except Exception:
                ok = False
            if ok:
                handle = await item.element_handle()
                if handle:
                    idv = await handle.get_attribute('id')
                    if idv:
                        return f"#{idv}", handle
                    namev = await handle.get_attribute('name')
                    if namev:
                        return f"[name="{namev}"]", handle
                    return f"[placeholder*="{ph}"]", handle
        return None

    async def find_by_role(self, role: str, name_pattern: Any):
        """Return (selector, element) for ARIA role + accessible name.
        Uses Playwright's get_by_role under the hood and synthesizes a selector.
        """
        assert self.page, "Call start() first"
        locator = self.page.get_by_role(role, name=name_pattern)
        count = await locator.count()
        if count == 0:
            return None
        handle = await locator.first.element_handle()
        if not handle:
            return None
        # Synthesize a stable-ish selector preference: id > name > [role][aria-label*=]
        idv = await handle.get_attribute('id')
        if idv:
            return f"#{idv}", handle
        namev = await handle.get_attribute('name')
        if namev:
            return f"[name="{namev}"]", handle
        # Try aria-label / text content path
        # NOTE: aria-label may not exist; fallback to role selector with name regex marker
        al = await handle.get_attribute('aria-label')
        if al:
            return f"[role="{role}"][aria-label*="{al}"]", handle
        return f"role={role}[name~="{getattr(name_pattern, 'pattern', str(name_pattern))}"]", handle

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self._pw:
            await self._pw.stop()
