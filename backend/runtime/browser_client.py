from __future__ import annotations
from typing import Optional, Tuple, Any
import re

def _is_valid_css_id(id_val: str) -> bool:
    """
    Check if ID can be safely used in CSS selector without escaping.

    CSS IDs containing special characters like parentheses, dots, or spaces
    are technically valid HTML but create invalid CSS selectors.

    Returns:
        True if ID contains only alphanumeric, hyphens, underscores
        False if ID contains special characters that need escaping
    """
    # Valid CSS ID: alphanumeric, hyphen, underscore only
    # Invalid: spaces, parentheses, dots, brackets, etc.
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', id_val))

def _escape_css_id(id_val: str) -> str:
    """
    Escape special characters in CSS ID selector.

    While we prefer avoiding IDs with special chars, this provides
    a fallback for edge cases.

    Args:
        id_val: Raw ID attribute value

    Returns:
        Escaped ID suitable for CSS selector
    """
    # Escape common special characters: . ( ) [ ] { }
    return re.sub(r'([.()\[\]{}])', r'\\\1', id_val)

def _synthesize_stable_selector(handle, role: Optional[str] = None, name_pattern: Optional[Any] = None) -> str:
    """
    Synthesize the most stable selector from element attributes.

    Priority:
        1. Valid ID (alphanumeric/hyphen/underscore only)
        2. name attribute
        3. data-test attribute (common in modern apps)
        4. Playwright semantic locator (role + name)

    This is an async function wrapper - call it synchronously with gathered attributes.
    """
    # This is actually synchronous - we gather attributes before calling
    pass

class BrowserClient:
    def __init__(self):
        self._pw = None
        self.browser = None
        self.page = None  # type: ignore

    async def start(self, headless: bool = True, project: str = "chromium", slow_mo: int = 0):
        """
        Start the browser instance.

        Args:
            headless: Run browser in headless mode (default: True)
            project: Browser type: chromium, firefox, webkit (default: chromium)
            slow_mo: Slow down operations by specified milliseconds (default: 0)
        """
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        if project == "chromium":
            self.browser = await self._pw.chromium.launch(headless=headless, slow_mo=slow_mo)
        elif project == "firefox":
            self.browser = await self._pw.firefox.launch(headless=headless, slow_mo=slow_mo)
        else:
            self.browser = await self._pw.webkit.launch(headless=headless, slow_mo=slow_mo)
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

    # --- Discovery helpers with selector validation ---
    async def find_by_label(self, text_pattern: Any):
        """
        Find input element by associated label text.

        Returns:
            Tuple of (validated_selector, element_handle) or None
        """
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
            # Validate ID before using as selector
            if _is_valid_css_id(for_attr):
                sel = f"#{for_attr}"
                el = await self.page.query_selector(sel)
                if el:
                    return sel, el
        inner = label.locator('input, textarea, [role="textbox"]')
        if await inner.count() > 0:
            handle = await inner.first.element_handle()
            if handle:
                # Try valid ID first
                idv = await handle.get_attribute('id')
                if idv and _is_valid_css_id(idv):
                    return f"#{idv}", handle
                # Try name attribute
                namev = await handle.get_attribute('name')
                if namev:
                    return f'[name="{namev}"]', handle
                # Fallback: use Playwright's text-based selector
                return 'xpath=.', handle
        return None

    async def find_by_placeholder(self, text_pattern: Any):
        """
        Find input element by placeholder attribute.

        Returns:
            Tuple of (validated_selector, element_handle) or None
        """
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
                    # Try valid ID first
                    idv = await handle.get_attribute('id')
                    if idv and _is_valid_css_id(idv):
                        return f"#{idv}", handle
                    # Try name attribute
                    namev = await handle.get_attribute('name')
                    if namev:
                        return f'[name="{namev}"]', handle
                    # Fallback: placeholder attribute selector
                    return f'[placeholder*="{ph}"]', handle
        return None

    async def find_by_role(self, role: str, name_pattern: Any):
        """
        Return (selector, element) for ARIA role + accessible name.

        Strategy:
            1. Use Playwright's get_by_role to find element
            2. Synthesize STABLE selector with validation
            3. Prefer Playwright semantic selectors over CSS when ID has special chars

        Returns:
            Tuple of (selector_string, element_handle) or None if not found
        """
        assert self.page, "Call start() first"
        locator = self.page.get_by_role(role, name=name_pattern)
        count = await locator.count()
        if count == 0:
            return None
        handle = await locator.first.element_handle()
        if not handle:
            return None

        # Priority 1: Valid CSS ID (no special characters)
        idv = await handle.get_attribute('id')
        if idv and _is_valid_css_id(idv):
            return f"#{idv}", handle

        # Priority 2: name attribute (common for form elements)
        namev = await handle.get_attribute('name')
        if namev and _is_valid_css_id(namev):
            return f'[name="{namev}"]', handle

        # Priority 3: data-test attribute (modern testing best practice)
        data_test = await handle.get_attribute('data-test')
        if data_test:
            # data-test values are usually safe for CSS
            return f'[data-test="{data_test}"]', handle

        # Priority 4: Playwright semantic locator (BEST for buttons with special chars)
        # This handles cases like "Test.allTheThings() T-Shirt (Red)"
        # Playwright locators are more robust than CSS selectors
        if isinstance(name_pattern, type(re.compile(''))):
            # It's a regex pattern
            name_str = name_pattern.pattern
        else:
            name_str = str(name_pattern)

        # Use Playwright's role-based selector (NOT CSS - this is Playwright syntax)
        # This works even with parentheses, dots, and other special characters
        return f'role={role}[name*="{name_str}"i]', handle

    # ==========================================
    # HEALING HELPERS (OracleHealer v2)
    # ==========================================

    async def scroll_into_view(self, selector: str) -> bool:
        """Scroll element into viewport (reveal strategy)."""
        assert self.page, "Call start() first"
        try:
            await self.page.locator(selector).first.scroll_into_view_if_needed(timeout=2000)
            return True
        except Exception:
            return False

    async def dismiss_overlays(self) -> int:
        """Try common overlay dismissal patterns. Returns count of dismissed overlays."""
        assert self.page, "Call start() first"
        dismissed = 0

        # Strategy 1: Press ESC (dismiss modals, popups)
        try:
            await self.page.keyboard.press("Escape", timeout=500)
            dismissed += 1
        except Exception:
            pass

        # Strategy 2: Click backdrop elements (common modal patterns)
        backdrop_selectors = [
            '.modal-backdrop',
            '[data-backdrop="static"]',
            '.overlay',
            '[aria-modal="false"]'
        ]
        for sel in backdrop_selectors:
            try:
                count = await self.page.locator(sel).count()
                if count > 0:
                    await self.page.locator(sel).first.click(timeout=500)
                    dismissed += 1
            except Exception:
                pass

        # Strategy 3: Find and click close buttons
        close_selectors = [
            'button[aria-label*="close" i]',
            'button[aria-label*="dismiss" i]',
            '[data-dismiss="modal"]',
            '.close',
            '.modal-close'
        ]
        for sel in close_selectors:
            try:
                count = await self.page.locator(sel).count()
                if count > 0:
                    await self.page.locator(sel).first.click(timeout=500)
                    dismissed += 1
            except Exception:
                pass

        return dismissed

    async def wait_network_idle(self, timeout_ms: int = 1000) -> bool:
        """Wait for network to be idle (no active requests)."""
        assert self.page, "Call start() first"
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout_ms)
            return True
        except Exception:
            return False

    async def incremental_scroll(self, pixels: int = 200) -> bool:
        """Scroll page by incremental amount (for lazy-loading UIs)."""
        assert self.page, "Call start() first"
        try:
            await self.page.evaluate(f"window.scrollBy(0, {pixels})")
            return True
        except Exception:
            return False

    async def bring_to_front(self) -> bool:
        """Bring page/tab to foreground."""
        assert self.page, "Call start() first"
        try:
            await self.page.bring_to_front()
            return True
        except Exception:
            return False

    async def wait_for_stability(self, selector: str, samples: int = 3, delay_ms: int = 200, tol: float = 2.0) -> bool:
        """Wait for element bbox to stabilize (animations, transitions)."""
        assert self.page, "Call start() first"
        try:
            el = await self.page.query_selector(selector)
            if not el:
                return False
            return await self.bbox_stable(el, samples=samples, delay_ms=delay_ms, tol=tol)
        except Exception:
            return False

    # ==========================================
    # END HEALING HELPERS
    # ==========================================

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self._pw:
            await self._pw.stop()
