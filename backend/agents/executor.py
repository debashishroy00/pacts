from __future__ import annotations
from typing import Dict, Any, Optional
import logging
import re
from ..graph.state import RunState, Failure
from ..runtime.browser_manager import BrowserManager
from ..runtime.policies import five_point_gate
from ..telemetry.tracing import traced
from ..mcp.mcp_client import USE_MCP
from .execution_helpers import press_with_fallbacks, fill_with_activator, handle_spa_navigation

logger = logging.getLogger(__name__)


async def _perform_action(browser, action: str, selector: str, value: Optional[str] = None) -> bool:
    """
    Execute a single action on an element.

    Uses local browser_client for all actions.
    NOTE: MCP actions disabled - MCP runs in separate browser instance,
    cannot access the PACTS browser being tested.

    Returns:
        bool: True if action succeeded, False otherwise
    """
    # Local browser_client action execution
    try:
        locator = browser.page.locator(selector)

        if action == "click":
            await locator.click(timeout=5000)
            return True

        elif action == "fill":
            if value is None:
                return False
            result = await fill_with_activator(browser, locator, selector, value)
            return result["success"]

        elif action == "type":
            if value is None:
                return False
            await locator.type(value, delay=50, timeout=5000)
            return True

        elif action == "press":
            if value is None:
                value = "Enter"  # default
            result = await press_with_fallbacks(browser, locator, selector, value)
            return result["success"]

        elif action == "select":
            if value is None:
                return False

            # Get element to detect type (Lightning combobox vs native select)
            element_handle = await locator.element_handle()
            role = await element_handle.get_attribute("role")
            tag_name = await element_handle.evaluate("el => el.tagName.toLowerCase()")

            # Lightning combobox (Salesforce pattern)
            if role == "combobox":
                print(f"[EXEC] 🔧 Lightning combobox detected: '{value}'")
                await locator.click(timeout=5000)
                await browser.page.wait_for_timeout(1000)  # Increased wait for dropdown render

                option = browser.page.get_by_role("option", name=re.compile(f"^{re.escape(value)}$", re.I))
                if await option.count() == 0:
                    print(f"[EXEC] ❌ Option '{value}' not found")
                    return False

                await option.first.click(timeout=5000)
                print(f"[EXEC] ✅ Selected '{value}'")
                return True

            # Native HTML select
            elif tag_name == "select":
                await locator.select_option(value, timeout=5000)
                return True

            # Fallback
            else:
                await locator.select_option(value, timeout=5000)
                return True

        elif action == "check":
            await locator.check(timeout=5000)
            return True

        elif action == "uncheck":
            await locator.uncheck(timeout=5000)
            return True

        elif action == "hover":
            await locator.hover(timeout=5000)
            return True

        elif action == "focus":
            await locator.focus(timeout=5000)
            return True

        else:
            # Unknown action
            return False

    except Exception as e:
        # Log the error but return False to trigger healing
        return False


async def _validate_step(browser, step: Dict[str, Any], heal_round: int = 0) -> tuple[Optional[Failure], Optional[Any]]:
    """
    Validate a step using MCP Playwright gates (if available) or local five_point_gate.

    Args:
        browser: BrowserClient instance
        step: Step dict with selector, action, value
        heal_round: Current healing round (for adaptive timeouts/tolerance)

    Returns:
        tuple: (Failure enum if failed, element handle if succeeded)
    """
    selector = step.get("selector")
    action = step.get("action", "click")

    if not selector:
        return Failure.timeout, None

    # If this is a press on the same element as last step, loosen validation
    if action == "press" and hasattr(browser, "last_selector_ok") and selector == browser.last_selector_ok:
        # Skip full gate check but still verify element exists and is visible
        print(f"[VALIDATE] Press-after-fill optimization triggered for {selector}")
        try:
            # Wait a moment for DOM to settle after autocomplete/fill
            await browser.page.wait_for_timeout(300)

            # Debug: Check if element exists at all
            count = await browser.page.locator(selector).count()
            print(f"[VALIDATE] Element count for {selector}: {count}")

            # Debug: Check what search inputs DO exist
            all_search_inputs = await browser.page.locator('input[type="search"], input[name="search"], input[placeholder*="earch"]').count()
            print(f"[VALIDATE] Total search-like inputs on page: {all_search_inputs}")

            # Re-query the element (it might have been replaced/moved in DOM)
            el = await browser.query(selector)
            print(f"[VALIDATE] Query result: {el}")
            if el:
                # Quick visibility check only (skip uniqueness since we proved it in last step)
                try:
                    is_visible = await el.is_visible()
                    if is_visible:
                        print(f"[VALIDATE] Press-after-fill optimization succeeded")
                        return None, el
                    else:
                        print(f"[VALIDATE] Press-after-fill: element exists but not visible")
                except Exception:
                    # If visibility check fails, element might be stale - continue to full validation
                    print(f"[VALIDATE] Press-after-fill: element stale, falling back to full validation")
            else:
                print(f"[VALIDATE] Press-after-fill: element not found, falling back to full validation")
        except Exception as e:
            print(f"[VALIDATE] Press-after-fill optimization error: {e}")
            pass

    # Query the element
    el = await browser.query(selector)
    if not el:
        return Failure.timeout, None

    # Run local five-point gate with healing-aware policies
    # Note: MCP can provide additional validation in the future
    gates = await five_point_gate(
        browser,
        selector,
        el,
        heal_round=heal_round,
        stabilize=False,  # Executor doesn't pre-stabilize (OracleHealer does)
        samples=3,
        timeout_ms=2000
    )

    # DIAGNOSTIC: Log gate results before checking
    print(f"[GATE] unique={gates['unique']} visible={gates['visible']} enabled={gates['enabled']} stable={gates['stable_bbox']} scoped={gates['scoped']} selector={selector}")

    # Check each gate and return appropriate failure
    if not gates["unique"]:
        return Failure.not_unique, None
    if not gates["visible"]:
        return Failure.not_visible, None
    if not gates["enabled"]:
        return Failure.disabled, None
    if not gates["stable_bbox"]:
        return Failure.unstable, None
    # scoped is always True for now (future: frame/shadow DOM)

    return None, el


@traced("executor")
async def run(state: RunState) -> RunState:
    """
    Executor Agent: Execute actions from the verified plan.

    Process:
    1. Get current step from plan using step_idx
    2. Validate element with five_point_gate
    3. Perform the action (click, fill, etc.)
    4. Update step_idx or set failure state

    State updates:
    - step_idx: incremented on success
    - failure: set to appropriate Failure enum on validation/action failure
    - last_selector: updated to current selector
    - context["executed_steps"]: list of successfully executed steps
    """
    # Pass browser config from context (for headed mode, slow_mo, etc.)
    browser_config = state.context.get("browser_config", {})
    browser = await BrowserManager.get(config=browser_config)

    # state.plan is a property that reads from context["plan"]
    plan = state.plan
    if not plan:
        # No plan to execute
        state.verdict = "fail"
        state.context["error"] = "Executor: No plan available"
        return state

    # Check if we've completed all steps
    if state.step_idx >= len(plan):
        # All steps executed successfully
        state.verdict = "pass"
        return state

    # Get current step
    step = plan[state.step_idx]
    selector = step.get("selector")
    action = step.get("action", "click")
    value = step.get("value")

    # MCP Actions Disabled (Phase A: Discovery-Only)
    # In Phase A, MCP only helps with discovery
    # All actions are executed locally by Playwright
    # Future Phase B: Enable MCP actions when attached to same browser (wsEndpoint)

    # HITL (Human-in-the-Loop) handling for "wait" action
    if action == "wait":
        print(f"[EXEC] HITL step detected: {step.get('element', 'Manual intervention')}")
        state.requires_human = True
        # Increment step_idx so when we return from human_wait, we proceed to next step
        state.step_idx += 1
        return state

    # Salesforce App Launcher search fallback
    if selector and selector.startswith("LAUNCHER_SEARCH:"):
        target = selector.split(":", 1)[1]
        print(f"[EXEC] Launcher search detected for: {target}")

        MAX_LAUNCHER_RETRIES = 2
        last_error = None

        for retry_attempt in range(MAX_LAUNCHER_RETRIES):
            try:
                # Find App Launcher dialog
                panel = browser.page.get_by_role("dialog", name=re.compile("app.?launcher", re.I))
                panel_count = await panel.count()

                if panel_count == 0:
                    raise Exception(f"App Launcher panel not found (retry {retry_attempt+1}/{MAX_LAUNCHER_RETRIES})")

                # Use search box
                search = panel.get_by_role("combobox", name=re.compile("search", re.I)).first
                # Clear any previous search text (important for retries)
                await search.clear()
                await browser.page.wait_for_timeout(500)
                await search.fill(target)
                await browser.page.wait_for_timeout(2000)  # Increased wait for search results to populate

                # Get current URL (to detect if clicking result navigates)
                old_url = browser.page.url

                # Try to click the result directly (don't press Enter - it might clear results)
                try:
                    # Click the result (button or link)
                    # Use more lenient pattern - match if target appears anywhere in name (not just exact match)
                    result_button = panel.get_by_role("button", name=re.compile(re.escape(target), re.I))
                    button_count = await result_button.count()

                    if button_count > 0:
                        await result_button.first.click(timeout=5000)
                        print(f"[EXEC] ✅ Clicked launcher result button for: {target}")
                        break  # Success
                    else:
                        # Try link
                        result_link = panel.get_by_role("link", name=re.compile(re.escape(target), re.I))
                        link_count = await result_link.count()
                        if link_count > 0:
                            await result_link.first.click(timeout=5000)
                            print(f"[EXEC] ✅ Clicked launcher result link for: {target}")
                            break  # Success
                        else:
                            # Try ANY element with text (Salesforce uses divs/spans with click handlers)
                            # BUT filter for clickable elements only (Option A: Filter by clickability)
                            result_text = panel.get_by_text(target, exact=False)
                            text_count = await result_text.count()
                            if text_count > 0:
                                print(f"[EXEC] 🔍 Found {text_count} elements with text '{target}', filtering for clickable ones...")

                                # Iterate through candidates and find the clickable one
                                clicked = False
                                for i in range(text_count):
                                    candidate = result_text.nth(i)
                                    try:
                                        # Check if element is clickable
                                        tag = await candidate.evaluate("el => el.tagName.toLowerCase()")
                                        href = await candidate.get_attribute("href")
                                        role = await candidate.get_attribute("role")
                                        classes = await candidate.get_attribute("class") or ""

                                        # Log for debugging
                                        print(f"[EXEC] 🔍   Candidate {i}: tag={tag} href={href} role={role} classes={classes[:50]}")

                                        # Filter: Skip section headings (usually divs without href)
                                        # Accept: <a> tags with href, or elements with role="link", or specific Salesforce classes
                                        is_clickable = (
                                            tag == "a" and href or  # Link with href
                                            role == "link" or       # ARIA link role
                                            "slds-truncate" in classes or  # Salesforce list item class
                                            "forceActionLink" in classes    # Salesforce action link
                                        )

                                        # If element itself isn't clickable, check parent (text nodes often nested in clickable containers)
                                        if not is_clickable:
                                            try:
                                                parent = await candidate.evaluate("el => el.parentElement")
                                                if parent:
                                                    parent_tag = await candidate.evaluate("el => el.parentElement.tagName.toLowerCase()")
                                                    parent_href = await candidate.evaluate("el => el.parentElement.getAttribute('href')")
                                                    parent_role = await candidate.evaluate("el => el.parentElement.getAttribute('role')")
                                                    parent_classes = await candidate.evaluate("el => el.parentElement.getAttribute('class')") or ""

                                                    is_clickable = (
                                                        parent_tag == "a" and parent_href or
                                                        parent_role == "link" or
                                                        "slds-truncate" in parent_classes or
                                                        "forceActionLink" in parent_classes
                                                    )
                                                    if is_clickable:
                                                        print(f"[EXEC] 🔍   Parent is clickable: {parent_tag}")
                                            except Exception:
                                                pass

                                        if is_clickable:
                                            await candidate.click(timeout=5000)
                                            print(f"[EXEC] ✅ Clicked clickable text element for: {target} (candidate {i})")
                                            clicked = True
                                            break
                                        else:
                                            print(f"[EXEC] 🔍   Skipping non-clickable element (candidate {i})")
                                    except Exception as e:
                                        print(f"[EXEC] ⚠️ Error checking candidate {i}: {e}")
                                        continue

                                if clicked:
                                    break  # Success
                                else:
                                    print(f"[EXEC] ❌ No clickable element found among {text_count} candidates")
                            else:
                                # MCP DEBUG: Inspect what's actually in the App Launcher
                                print(f"[EXEC] 🔍 MCP Debug: Inspecting App Launcher contents for '{target}'...")
                                try:
                                    # Get all buttons in the panel
                                    all_buttons = panel.get_by_role("button")
                                    button_total = await all_buttons.count()
                                    print(f"[EXEC] 🔍 Found {button_total} buttons in App Launcher")

                                    # Sample first 10 button names
                                    for i in range(min(10, button_total)):
                                        btn = all_buttons.nth(i)
                                        btn_text = await btn.inner_text()
                                        btn_name = await btn.get_attribute("aria-label") or btn_text
                                        print(f"[EXEC] 🔍   Button {i}: '{btn_name}' (text: '{btn_text}')")

                                    # Get all links in the panel
                                    all_links = panel.get_by_role("link")
                                    link_total = await all_links.count()
                                    print(f"[EXEC] 🔍 Found {link_total} links in App Launcher")

                                    # Sample first 10 link names
                                    for i in range(min(10, link_total)):
                                        link = all_links.nth(i)
                                        link_text = await link.inner_text()
                                        link_name = await link.get_attribute("aria-label") or link_text
                                        print(f"[EXEC] 🔍   Link {i}: '{link_name}' (text: '{link_text}')")

                                    # ALSO check for ANY element containing the target text (not just button/link)
                                    print(f"[EXEC] 🔍 Searching for ANY element with text '{target}'...")
                                    text_locator = panel.get_by_text(target, exact=False)
                                    text_count = await text_locator.count()
                                    print(f"[EXEC] 🔍 Found {text_count} elements containing '{target}'")

                                    for i in range(min(5, text_count)):
                                        elem = text_locator.nth(i)
                                        elem_text = await elem.inner_text()
                                        elem_role = await elem.get_attribute("role")
                                        elem_tag = await elem.evaluate("el => el.tagName")
                                        print(f"[EXEC] 🔍   Element {i}: tag='{elem_tag}' role='{elem_role}' text='{elem_text}'")
                                except Exception as debug_error:
                                    print(f"[EXEC] ⚠️ MCP debug failed: {debug_error}")

                                raise Exception(f"No results found for '{target}' in App Launcher")
                except Exception as click_error:
                    # Even if click fails, check if we navigated successfully
                    new_url = browser.page.url
                    if new_url != old_url:
                        print(f"[EXEC] ✅ Navigation detected despite click error: {new_url}")
                        break  # Success
                    else:
                        raise click_error

            except Exception as e:
                last_error = e

                if retry_attempt < MAX_LAUNCHER_RETRIES - 1:
                    # Retry logic
                    print(f"[EXEC] ⚠️ Launcher search retry {retry_attempt+1}/{MAX_LAUNCHER_RETRIES} for: {target}")

                    # Close and reopen App Launcher
                    await browser.page.keyboard.press("Escape")
                    await browser.page.wait_for_timeout(500)

                    app_launcher_button = browser.page.get_by_role("button", name=re.compile("app.?launcher", re.I))
                    await app_launcher_button.first.click()
                    await browser.page.wait_for_timeout(1000)

                    continue  # Try again
                else:
                    # Final retry failed
                    print(f"[EXEC] ❌ Launcher search failed after {MAX_LAUNCHER_RETRIES} retries: {target}")
                    print(f"[EXEC] Diagnostics: url={browser.page.url}, last_error={str(last_error)}")
                    state.failure = Failure.timeout
                    return state

        print(f"[EXEC] Launcher search succeeded for: {target}")

        # Mark step as complete
        state.step_idx += 1
        state.failure = Failure.none
        if "executed_steps" not in state.context:
            state.context["executed_steps"] = []
        state.context["executed_steps"].append({
            "step_idx": state.step_idx - 1,
            "selector": selector,
            "action": action,
            "method": "launcher_search"
        })

        # Take screenshot
        try:
            import os
            from pathlib import Path
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            req_id = state.req_id or "unknown"
            step_num = state.step_idx - 1
            element_name = step.get("element", target).replace(" ", "_").replace("/", "_")
            screenshot_path = screenshots_dir / f"{req_id}_step{step_num:02d}_{element_name}.png"
            await browser.page.screenshot(path=str(screenshot_path))
            print(f"[EXEC] Screenshot saved: {screenshot_path}")
        except Exception:
            pass

        return state

    # Update last_selector for healing
    state.last_selector = selector

    # Store current URL to detect navigation
    url_before = browser.page.url

    # Debug: Log browser.last_selector_ok status and URL
    current_url = browser.page.url if browser and browser.page else "NO_URL"
    if hasattr(browser, "last_selector_ok"):
        print(f"[EXEC] URL={current_url} last_selector_ok={browser.last_selector_ok}, current selector={selector}, action={action}, match={browser.last_selector_ok == selector}")
    else:
        print(f"[EXEC] URL={current_url} No last_selector_ok attribute on browser yet, current selector={selector}, action={action}")

    # SPECIAL CASE: Press-after-fill on same element with autocomplete bypass
    # If the element was just filled and now we're pressing Enter, skip validation
    # and go straight to submit button (Wikipedia removes #searchInput after fill)
    if (action == "press" and
        hasattr(browser, "last_selector_ok") and
        selector == browser.last_selector_ok and
        value in (None, "Enter")):
        print(f"[EXEC] Press-after-fill detected - attempting autocomplete bypass without validation")
        # Try clicking the search/submit button directly (element might have been removed from DOM)
        success = False

        # Strategy 1: Try Wikipedia-specific search button
        try:
            submit_button = browser.page.locator("#searchButton").first
            await submit_button.click(timeout=2000)
            print(f"[EXEC] Autocomplete bypass succeeded - clicked #searchButton")
            success = True
        except Exception as e1:
            print(f"[EXEC] Strategy 1 failed (#searchButton): {e1}")

            # Strategy 2: Try visible submit button within search form
            if not success:
                try:
                    # Find any submit button that's visible
                    submit_button = browser.page.locator("button[type='submit']").first
                    if await submit_button.is_visible():
                        await submit_button.click(timeout=2000)
                        print(f"[EXEC] Autocomplete bypass succeeded - clicked visible submit button")
                        success = True
                    else:
                        print(f"[EXEC] Strategy 2: submit button exists but not visible")
                except Exception as e2:
                    print(f"[EXEC] Strategy 2 failed (submit button): {e2}")

            # Strategy 3: Just press Enter on the page (fallback)
            if not success:
                try:
                    await browser.page.keyboard.press("Enter")
                    print(f"[EXEC] Autocomplete bypass succeeded - pressed Enter via keyboard")
                    success = True
                except Exception as e3:
                    print(f"[EXEC] Strategy 3 failed (keyboard Enter): {e3}")
                    print(f"[EXEC] All autocomplete bypass strategies failed - falling back to normal validation")

        if success:
            # Skip validation, go straight to post-action processing
            browser.last_selector_ok = selector
            state.failure = Failure.none
            state.step_idx += 1
            if "executed_steps" not in state.context:
                state.context["executed_steps"] = []
            state.context["executed_steps"].append({
                "step_idx": state.step_idx - 1,
                "selector": selector,
                "action": action,
                "value": value,
                "heal_round": state.heal_round,
                "autocomplete_bypass": True
            })
            # Take screenshot
            try:
                import os
                from pathlib import Path
                screenshots_dir = Path("screenshots")
                screenshots_dir.mkdir(exist_ok=True)
                req_id = state.req_id or "unknown"
                step_num = state.step_idx - 1
                element_name = step.get("element", "unknown").replace(" ", "_").replace("/", "_")
                screenshot_path = screenshots_dir / f"{req_id}_step{step_num:02d}_{element_name}.png"
                await browser.page.screenshot(path=str(screenshot_path))
                print(f"[EXEC] Screenshot saved: {screenshot_path}")
            except Exception:
                pass
            return state

    # Normal path: Validate element with five_point gate
    failure, el = await _validate_step(browser, step, heal_round=state.heal_round)

    if failure:
        # Validation failed - set failure state for healing
        state.failure = failure
        return state

    # Perform the action
    success = await _perform_action(browser, action, selector, value)

    if not success:
        # Action failed - mark as timeout for healing
        state.failure = Failure.timeout
        return state

    # Remember last successful selector for press-after-fill optimization
    browser.last_selector_ok = selector

    # NAVIGATION-AWARE SUCCESS DETECTION: Race between URL navigation and DOM success tokens
    # Handles cases like Wikipedia where DOM changes occur before URL changes
    if action in ("press", "click"):
        try:
            # Create navigation waiter (may not complete if SPA/AJAX)
            nav_task = None
            try:
                nav_task = browser.page.wait_for_navigation(timeout=4000)
            except Exception:
                pass

            # Create DOM success token waiter (article loaded, search results visible)
            dom_task = None
            try:
                dom_task = browser.page.wait_for_selector("#firstHeading, [data-search-results]", timeout=4000)
            except Exception:
                pass

            # Race: succeed if EITHER navigation OR DOM token appears
            if nav_task or dom_task:
                try:
                    if nav_task and dom_task:
                        # Wait for whichever completes first
                        import asyncio
                        await asyncio.wait([nav_task, dom_task], return_when=asyncio.FIRST_COMPLETED, timeout=4.0)
                    elif nav_task:
                        await nav_task
                    elif dom_task:
                        await dom_task

                    # Success detected via navigation or DOM token
                    state.context["navigation_occurred"] = True
                    logger.info("[EXEC] Navigation/DOM success detected")
                except Exception:
                    # Timeout or error - continue without marking navigation
                    pass
        except Exception:
            # Non-critical - continue execution
            pass

    # Capture screenshot after successful action (for documentation)
    try:
        import os
        from pathlib import Path
        screenshots_dir = Path("screenshots")
        screenshots_dir.mkdir(exist_ok=True)

        req_id = state.req_id or "unknown"
        step_num = state.step_idx
        element_name = step.get("element", "unknown").replace(" ", "_").replace("/", "_")

        screenshot_path = screenshots_dir / f"{req_id}_step{step_num:02d}_{element_name}.png"
        await browser.page.screenshot(path=str(screenshot_path))
        logger.info(f"[EXEC] Screenshot saved: {screenshot_path}")
    except Exception as e:
        logger.debug(f"[EXEC] Screenshot failed (non-critical): {e}")

    # Check if navigation occurred
    url_after = browser.page.url
    navigation_occurred = url_before != url_after
    if navigation_occurred:
        # Store navigation flag for healer to know not to reprobe
        state.context["navigation_occurred"] = True
        state.context["navigation_step"] = state.step_idx

    # NAVIGATION AWARENESS: Wait for page to settle after actions that navigate
    expected = step.get("expected") or ""
    if expected and expected.startswith("navigates_to:"):
        try:
            # Wait for network to be idle (AJAX, page load complete)
            await browser.page.wait_for_load_state("networkidle", timeout=5000)
            # Additional settle time for animations/JS execution
            await browser.page.wait_for_timeout(200)
        except Exception:
            # Non-blocking - continue even if navigation wait times out
            pass

    # Success! Update state
    state.failure = Failure.none
    state.step_idx += 1

    # Track executed steps in context
    if "executed_steps" not in state.context:
        state.context["executed_steps"] = []
    state.context["executed_steps"].append({
        "step_idx": state.step_idx - 1,
        "selector": selector,
        "action": action,
        "value": value,
        "heal_round": state.heal_round
    })

    return state
