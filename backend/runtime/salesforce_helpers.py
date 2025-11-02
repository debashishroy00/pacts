"""
Salesforce Lightning-specific execution helpers.

This module contains patterns and utilities specific to Salesforce Lightning Experience.
Keeps the core executor.py framework-agnostic while supporting enterprise SPA testing.
"""

from typing import Optional, Any
import re


async def handle_launcher_search(browser, target: str) -> bool:
    """
    Handle Salesforce App Launcher search pattern.

    Salesforce Lightning uses a modal dialog with search functionality
    to navigate to different objects/apps. This is a distinct pattern from
    standard navigation.

    Args:
        browser: Browser client instance
        target: The item to search for (e.g., "Opportunities", "Accounts")

    Returns:
        bool: True if navigation succeeded, False otherwise
    """
    print(f"[SALESFORCE] Launcher search for: {target}")

    MAX_RETRIES = 2
    last_error = None

    for retry_attempt in range(MAX_RETRIES):
        try:
            # Find App Launcher dialog
            panel = browser.page.get_by_role("dialog", name=re.compile("app.?launcher", re.I))
            panel_count = await panel.count()

            if panel_count == 0:
                raise Exception(f"App Launcher panel not found (retry {retry_attempt+1}/{MAX_RETRIES})")

            # Use search box
            search = panel.get_by_role("combobox", name=re.compile("search", re.I)).first
            await search.clear()  # Clear previous search
            await search.fill(target)
            await browser.page.wait_for_timeout(500)  # Wait for results

            # Track URL for navigation detection
            old_url = browser.page.url

            # Try exact button/link match first
            try:
                result = panel.get_by_role("link", name=re.compile(f"^{re.escape(target)}$", re.I))
                if await result.count() > 0:
                    await result.first.click(timeout=5000)
                    print(f"[SALESFORCE] ✅ Clicked exact link match: {target}")
                    return True
            except Exception:
                pass

            # Try text-based search with clickability filter
            result_text = panel.get_by_text(target, exact=False)
            text_count = await result_text.count()

            if text_count > 0:
                print(f"[SALESFORCE] 🔍 Found {text_count} elements, filtering for clickable...")

                # Filter for clickable elements
                for i in range(text_count):
                    try:
                        candidate = result_text.nth(i)
                        tag = await candidate.evaluate("el => el.tagName.toLowerCase()")
                        href = await candidate.get_attribute("href")
                        role = await candidate.get_attribute("role")
                        classes = await candidate.get_attribute("class") or ""

                        # Salesforce-specific clickable patterns
                        is_clickable = (
                            tag == "a" and href or
                            role == "link" or
                            "slds-truncate" in classes or  # Salesforce list item
                            "forceActionLink" in classes   # Salesforce action link
                        )

                        # Check parent if element itself isn't clickable
                        if not is_clickable:
                            try:
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
                                    print(f"[SALESFORCE] 🔍 Parent is clickable: {parent_tag}")
                            except Exception:
                                pass

                        if is_clickable:
                            await candidate.click(timeout=5000)
                            print(f"[SALESFORCE] ✅ Clicked clickable element: {target}")

                            # Check if navigation occurred
                            await browser.page.wait_for_timeout(1000)
                            if browser.page.url != old_url:
                                print(f"[SALESFORCE] ✅ Navigation confirmed")
                                return True
                            else:
                                print(f"[SALESFORCE] ⚠️ Click succeeded but no navigation")
                                return True  # Consider success even without URL change
                    except Exception as e:
                        continue

                print(f"[SALESFORCE] ❌ No clickable element found among {text_count} candidates")

            # If we get here, no results found
            raise Exception(f"No results found for '{target}' in App Launcher")

        except Exception as e:
            last_error = e

            # Check if navigation happened despite error
            new_url = browser.page.url
            if new_url != old_url:
                print(f"[SALESFORCE] ✅ Navigation detected despite error: {new_url}")
                return True

            # Retry logic
            if retry_attempt < MAX_RETRIES - 1:
                print(f"[SALESFORCE] ⚠️ Retry {retry_attempt+1}/{MAX_RETRIES} for: {target}")

                # Close and reopen App Launcher
                await browser.page.keyboard.press("Escape")
                await browser.page.wait_for_timeout(500)

                app_launcher_button = browser.page.get_by_role("button", name=re.compile("app.?launcher", re.I))
                await app_launcher_button.first.click()
                await browser.page.wait_for_timeout(500)

    # All retries exhausted
    print(f"[SALESFORCE] ❌ Failed after {MAX_RETRIES} retries: {last_error}")
    return False


async def handle_lightning_combobox(browser, locator, value: str) -> bool:
    """
    Handle Salesforce Lightning combobox (custom dropdown) selection.

    Lightning comboboxes are custom components that don't use native <select>.
    They require clicking to open, waiting for options to render, then selecting.

    Args:
        browser: Browser client instance
        locator: Playwright locator for the combobox
        value: The option value to select

    Returns:
        bool: True if selection succeeded, False otherwise
    """
    print(f"[SALESFORCE] 🔧 Lightning combobox detected: '{value}'")

    # Click to open dropdown
    await locator.click(timeout=5000)
    await browser.page.wait_for_timeout(2000)  # Wait for dropdown to render

    # Try exact match first
    option = browser.page.get_by_role("option", name=re.compile(f"^{re.escape(value)}$", re.I))
    option_count = await option.count()

    # Try partial match if exact fails
    if option_count == 0:
        print(f"[SALESFORCE] 🔍 Exact match failed, trying partial match...")
        option = browser.page.get_by_role("option", name=re.compile(re.escape(value), re.I))
        option_count = await option.count()

    # Fallback strategies if still not found
    if option_count == 0:
        print(f"[SALESFORCE] 🔍 Trying fallback strategies...")

        # Try listitem role
        all_options = browser.page.get_by_role("listitem")
        total_options = await all_options.count()

        if total_options > 0:
            for i in range(total_options):
                try:
                    opt = all_options.nth(i)
                    opt_text = (await opt.inner_text()).strip()

                    if opt_text and value.lower() in opt_text.lower():
                        print(f"[SALESFORCE] ✅ Found '{value}' in listitem, clicking...")
                        await opt.click(timeout=5000)
                        print(f"[SALESFORCE] ✅ Selected '{value}'")
                        return True
                except Exception:
                    continue

        # Final fallback: plain text search
        text_option = browser.page.get_by_text(value, exact=True)
        if await text_option.count() > 0:
            await text_option.first.click(timeout=5000)
            print(f"[SALESFORCE] ✅ Selected '{value}' via text search")
            return True

        print(f"[SALESFORCE] ❌ Option '{value}' not found after all attempts")
        return False

    # Found via role="option"
    await option.first.click(timeout=5000)
    print(f"[SALESFORCE] ✅ Selected '{value}'")
    return True


def is_launcher_search(selector: str) -> bool:
    """Check if selector is a Salesforce App Launcher search pattern."""
    return selector and selector.startswith("LAUNCHER_SEARCH:")


def extract_launcher_target(selector: str) -> str:
    """Extract target name from LAUNCHER_SEARCH:target selector."""
    return selector.split(":", 1)[1] if is_launcher_search(selector) else ""
