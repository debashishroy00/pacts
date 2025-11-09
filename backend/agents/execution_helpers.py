"""
Execution Helper Functions

Extracted patterns for clean, testable, reusable action execution.
Each helper encapsulates a specific interaction pattern.
"""

import logging
from typing import Optional
from playwright.async_api import Locator, Page
from ..runtime.patterns import ExecutionPatterns

logger = logging.getLogger(__name__)


async def ensure_fillable(page: Page, locator: Locator) -> Locator:
    """
    Action-aware targeting: If locator points to a non-editable element (button, div),
    activate the UI and re-target an actual editable input.

    Critical fix for GitHub/search scenarios where discovery returns button instead of input.

    Args:
        page: Playwright page
        locator: Original locator (may be button/non-editable)

    Returns:
        Editable locator (input/textarea) or raises exception

    Raises:
        Exception: "element_hidden" if no fillable element found after activation
    """
    import re

    try:
        # Check if already editable
        is_editable = await locator.is_editable()
        if is_editable:
            return locator
    except Exception:
        pass  # May not exist yet

    logger.info("[EXEC] ensure_fillable: Element not editable, attempting activation + re-targeting")

    # Step 1: Try common activators for search/header inputs
    activators = [
        'button[aria-label="Search"]',
        'button[aria-label="Toggle navigation"]',  # GitHub hamburger menu
        'button:has(svg[aria-label="Search"])',     # Icon buttons
        'label[for="query-builder-test"]',          # GitHub label
        '[data-action="focus-query-builder"]',      # GitHub data attrs
    ]

    for sel in activators:
        try:
            act = page.locator(sel).first
            if await act.is_visible():
                logger.info(f"[EXEC] ensure_fillable: Clicking activator: {sel}")
                await act.click(timeout=2000)
                await page.wait_for_timeout(150)
                break
        except Exception:
            continue

    # Step 2: Re-target editable search input (priority order)
    candidates = [
        page.get_by_role("searchbox"),                          # Preferred (semantic)
        page.get_by_placeholder(re.compile(r"search|jump to", re.I)),  # GitHub: "Search or jump to…"
        page.locator('input[type="search"]'),                   # Standard search input
        page.locator('input[name="q"]'),                        # Common query param
        page.locator('input[name="query-builder-test"]'),       # GitHub specific
        page.locator('input[aria-label*="Search"]'),            # Aria label
    ]

    for cand in candidates:
        try:
            first = cand.first
            if await first.is_visible() and await first.is_editable():
                logger.info(f"[EXEC] ensure_fillable: Found editable input via candidate")
                return first
        except Exception:
            continue

    # Step 3: Last-resort hotkey (GitHub focuses search with '/')
    try:
        logger.info("[EXEC] ensure_fillable: Trying '/' hotkey to focus search")
        await page.keyboard.press('/')
        await page.wait_for_timeout(100)

        sb = page.get_by_role("searchbox").first
        if await sb.is_visible() and await sb.is_editable():
            logger.info("[EXEC] ensure_fillable: Hotkey successful")
            return sb
    except Exception:
        pass

    # All strategies failed
    logger.error("[EXEC] ensure_fillable: No editable input found after activation")
    raise Exception("element_hidden")


async def press_with_fallbacks(browser, locator, selector: str, value: str = "Enter") -> dict:
    """
    Press key with multi-strategy fallback chain.

    Strategy priority:
    1. Autocomplete bypass (if detected) - click submit button
    2. Direct press on element
    3. Click submit button in ancestor form
    4. Call form.submit() via JavaScript

    Args:
        browser: BrowserClient instance
        locator: Playwright locator for the element
        selector: CSS selector (for form scoping)
        value: Key to press (default "Enter")

    Returns:
        dict with keys:
            - success: bool
            - strategy: str (which strategy worked)
            - ms: int (execution time)
    """
    import time
    start_ms = time.time() * 1000

    # Always ensure element is focused first
    try:
        await locator.scroll_into_view_if_needed()
        await locator.focus()
    except Exception:
        pass

    # Strategy 0: Autocomplete bypass (pre-check)
    if value == "Enter":
        try:
            autocomplete_visible = await ExecutionPatterns.detect_autocomplete(browser.page)
            if autocomplete_visible:
                logger.debug("[EXEC] Autocomplete detected - attempting bypass")

                # Try submit buttons in priority order
                for submit_selector in ExecutionPatterns.get_submit_selectors():
                    try:
                        submit = browser.page.locator(submit_selector).first
                        if await submit.is_visible():
                            await submit.click(timeout=3000)
                            elapsed = int(time.time() * 1000 - start_ms)
                            logger.info(f"[EXEC] strategy=autocomplete_bypass selector={submit_selector} ms={elapsed}")
                            return {"success": True, "strategy": "autocomplete_bypass", "ms": elapsed}
                    except Exception:
                        continue

                # If no submit button found, try form-scoped submit
                try:
                    form = browser.page.locator("form").filter(has=locator).first
                    submit = form.locator('button[type="submit"], input[type="submit"]').first
                    await submit.click(timeout=3000)
                    elapsed = int(time.time() * 1000 - start_ms)
                    logger.info(f"[EXEC] strategy=autocomplete_bypass_form ms={elapsed}")
                    return {"success": True, "strategy": "autocomplete_bypass_form", "ms": elapsed}
                except Exception as e:
                    logger.debug(f"[EXEC] Autocomplete bypass failed: {e}")
        except Exception:
            pass

    # Strategy 1: Direct press
    try:
        logger.debug(f"[EXEC] Press strategy=direct_press key={value}")
        await locator.press(value, timeout=3000)
        elapsed = int(time.time() * 1000 - start_ms)
        logger.info(f"[EXEC] strategy=direct_press ms={elapsed}")
        return {"success": True, "strategy": "direct_press", "ms": elapsed}
    except Exception as e1:
        logger.debug(f"[EXEC] direct_press failed: {e1}")

    # Strategy 2: Click submit in ancestor form
    try:
        logger.debug("[EXEC] Press strategy=form_submit_button")
        form = browser.page.locator("form").filter(has=locator).first
        submit = form.locator('button[type="submit"], input[type="submit"]').first
        await submit.click(timeout=2000)
        elapsed = int(time.time() * 1000 - start_ms)
        logger.info(f"[EXEC] strategy=form_submit_button ms={elapsed}")
        return {"success": True, "strategy": "form_submit_button", "ms": elapsed}
    except Exception as e2:
        logger.debug(f"[EXEC] form_submit_button failed: {e2}")

    # Strategy 3: JavaScript form.submit()
    try:
        logger.debug("[EXEC] Press strategy=form_submit_js")
        ok = await locator.evaluate('el => { const f = el.closest("form"); if (f) { f.submit(); return true; } return false; }')
        if ok:
            elapsed = int(time.time() * 1000 - start_ms)
            logger.info(f"[EXEC] strategy=form_submit_js ms={elapsed}")
            return {"success": True, "strategy": "form_submit_js", "ms": elapsed}
    except Exception as e3:
        logger.debug(f"[EXEC] form_submit_js failed: {e3}")

    # All strategies failed
    elapsed = int(time.time() * 1000 - start_ms)
    logger.error(f"[EXEC] strategy=all_failed action=press ms={elapsed}")
    return {"success": False, "strategy": "all_failed", "ms": elapsed}


async def fill_with_activator(browser, locator, selector: str, value: str) -> dict:
    """
    Fill input with activator-first pattern and hidden element activation (v3.1s Phase 4a-B).

    Phase 4a-B Enhancement: When input is hidden, auto-activate the UI first.
    Common scenarios:
    - Collapsed search bars (GitHub, StackOverflow)
    - Click-to-reveal inputs (modern SPAs)
    - Hidden inputs in dropdowns/popovers

    Execution flow:
    1. Check if element is visible
    2. If hidden, try common activators (Search button, icon, etc.)
    3. If activator pattern detected (modal/overlay triggers), handle that
    4. Fill the input

    Args:
        browser: BrowserClient instance
        locator: Playwright locator for the element
        selector: CSS selector
        value: Text to fill

    Returns:
        dict with keys:
            - success: bool
            - strategy: str
            - ms: int
    """
    import time
    start_ms = time.time() * 1000

    # Phase 4a-B: Hidden Element Activation (v3.1s Stealth 2.0)
    # Check if element is hidden and needs activation
    try:
        is_visible = await locator.is_visible()
        if not is_visible:
            logger.info("[EXEC] Phase 4a-B: Element hidden, attempting activation")

            # Try common activators for search/input fields
            activator_candidates = [
                ('button[aria-label*="Search"]', 'aria-label search'),
                ('button:has-text("Search")', 'text search'),
                ('[data-test-id*="search"]', 'data-test search'),
                ('button.search-button', 'class search'),
                ('[role="button"]:has-text("Search")', 'role search'),
                ('button[aria-label="Toggle navigation"]', 'hamburger nav'),  # GitHub mobile/small viewports
                # Icons and UI triggers
                ('svg[aria-label*="Search"]', 'svg search'),
                ('.search-icon', 'search icon'),
                ('[type="search"] + button', 'search adjacent button')
            ]

            for activator_selector, desc in activator_candidates:
                try:
                    activator = browser.page.locator(activator_selector).first
                    if await activator.is_visible():
                        logger.info(f"[EXEC] Phase 4a-B: Clicking activator ({desc})")
                        await activator.click(timeout=2000)
                        await browser.page.wait_for_timeout(150)  # Small settle time

                        # Re-check if target element is now visible
                        if await locator.is_visible():
                            logger.info(f"[EXEC] Phase 4a-B: Activation successful via {desc}")
                            break
                except Exception:
                    continue

            # Final visibility check
            if not await locator.is_visible():
                elapsed = int(time.time() * 1000 - start_ms)
                logger.error(f"[EXEC] Phase 4a-B: Element still hidden after activation attempts, ms={elapsed}")
                return {"success": False, "strategy": "element_hidden", "ms": elapsed}

            logger.info("[EXEC] Phase 4a-B: Element now visible after activation")

    except Exception as e:
        logger.debug(f"[EXEC] Phase 4a-B: Visibility check failed: {e}")

    # Original activator pattern detection (modal/overlay triggers)
    try:
        element_role = await locator.get_attribute("role")
        element_type = await locator.get_attribute("type")
        tag_name = await locator.evaluate("el => el.tagName.toLowerCase()")

        is_activator = ExecutionPatterns.is_activator(tag_name, element_type, element_role, selector)

        if is_activator:
            logger.info(f"[EXEC] Activator detected: tag={tag_name} role={element_role} type={element_type}")

            # Click the activator to reveal actual input
            await locator.click(timeout=3000)
            await browser.page.wait_for_timeout(ExecutionPatterns.ACTIVATOR["post_click_wait_ms"])

            # Try to find the actual input that appeared
            for input_selector in ExecutionPatterns.get_activator_input_selectors():
                try:
                    actual_input = browser.page.locator(input_selector).first
                    if await actual_input.is_visible():
                        await actual_input.fill(value, timeout=3000)
                        elapsed = int(time.time() * 1000 - start_ms)
                        logger.info(f"[EXEC] strategy=activator_fill selector={input_selector} ms={elapsed}")
                        return {"success": True, "strategy": "activator_fill", "ms": elapsed}
                except Exception:
                    continue

            # If no visible input found, try filling the activator itself
            logger.debug("[EXEC] No visible input after activator click, trying activator itself")

    except Exception as e:
        logger.debug(f"[EXEC] Activator detection failed: {e}")

    # Normal fill (not an activator, or activator pattern failed)
    # Apply ensure_fillable for action-aware targeting (GitHub button→input fix)
    try:
        target = await ensure_fillable(browser.page, locator)
        await target.fill(value, timeout=5000)
        elapsed = int(time.time() * 1000 - start_ms)
        logger.info(f"[EXEC] strategy=direct_fill ms={elapsed}")
        return {"success": True, "strategy": "direct_fill", "ms": elapsed}
    except Exception as e:
        elapsed = int(time.time() * 1000 - start_ms)
        logger.error(f"[EXEC] strategy=fill_failed error={e} ms={elapsed}")
        return {"success": False, "strategy": "fill_failed", "ms": elapsed}


async def handle_spa_navigation(browser, action: str, step: dict) -> dict:
    """
    Handle SPA navigation with race condition detection.

    For actions that trigger navigation (press, click), race between:
    - URL navigation completion
    - Success DOM tokens appearing

    Args:
        browser: BrowserClient instance
        action: Action type ("press", "click", etc.)
        step: Step dictionary (for context)

    Returns:
        dict with keys:
            - navigation_occurred: bool
            - strategy: str
            - ms: int
    """
    import time
    import asyncio

    if action not in ExecutionPatterns.SPA_NAV["actions"]:
        return {"navigation_occurred": False, "strategy": "not_applicable", "ms": 0}

    start_ms = time.time() * 1000

    try:
        # Determine site hint from URL or context
        current_url = browser.page.url.lower()
        site_hint = None
        if "wikipedia" in current_url:
            site_hint = "wikipedia"
        elif "github" in current_url:
            site_hint = "github"

        # Get success tokens for this site
        success_selectors = ExecutionPatterns.get_spa_success_tokens(site_hint)

        # Create navigation waiter
        nav_task = None
        try:
            nav_task = asyncio.create_task(
                browser.page.wait_for_navigation(timeout=ExecutionPatterns.SPA_NAV["timeout_ms"])
            )
        except Exception:
            pass

        # Create DOM success token waiter
        dom_task = None
        try:
            # Combine all success selectors with OR
            combined_selector = ", ".join(success_selectors)
            dom_task = asyncio.create_task(
                browser.page.wait_for_selector(combined_selector, timeout=ExecutionPatterns.SPA_NAV["timeout_ms"])
            )
        except Exception:
            pass

        # Race: whichever completes first wins
        if nav_task or dom_task:
            tasks = [t for t in [nav_task, dom_task] if t]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=4.0)

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            if done:
                elapsed = int(time.time() * 1000 - start_ms)
                logger.info(f"[EXEC] strategy=spa_nav_success site={site_hint} ms={elapsed}")
                return {"navigation_occurred": True, "strategy": "spa_nav_success", "ms": elapsed}

    except Exception as e:
        logger.debug(f"[EXEC] SPA navigation detection failed: {e}")

    return {"navigation_occurred": False, "strategy": "spa_nav_timeout", "ms": int(time.time() * 1000 - start_ms)}
