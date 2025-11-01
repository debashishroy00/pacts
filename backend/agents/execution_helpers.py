"""
Execution Helper Functions

Extracted patterns for clean, testable, reusable action execution.
Each helper encapsulates a specific interaction pattern.
"""

import logging
from typing import Optional
from ..runtime.patterns import ExecutionPatterns

logger = logging.getLogger(__name__)


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
    Fill input with activator-first pattern.

    Detects if element is a button/trigger that opens a modal with the actual input.
    If activator detected:
    1. Click the activator
    2. Wait for modal/overlay
    3. Find actual input field
    4. Fill the actual input

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

    # Detect if this is an activator
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
    try:
        await locator.fill(value, timeout=5000)
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
