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

    Uses a robust multi-strategy approach to handle Lightning's various picklist
    rendering modes (standard, custom fields, portals, shadow DOM).

    Priority order:
    1. Type-ahead (bypasses DOM quirks - works even when options aren't queryable)
    2. aria-controls listbox targeting (scoped search with role fallbacks)
    3. Keyboard navigation (arrow down + enter - sidesteps all DOM issues)

    Args:
        browser: Browser client instance
        locator: Playwright locator for the combobox
        value: The option value to select

    Returns:
        bool: True if selection succeeded, False otherwise
    """
    print(f"[SALESFORCE] 🔧 Lightning combobox: '{value}'")

    # Get the input element for type-ahead
    element_handle = await locator.element_handle()

    # STRATEGY 1: Type-ahead (most robust - bypasses options DOM)
    # Lightning filters internally, works even when options aren't queryable
    try:
        print(f"[SALESFORCE] 🎯 Strategy 1: Type-ahead")
        await locator.click(timeout=5000)
        await browser.page.wait_for_timeout(300)  # Wait for dropdown to open

        # Focus the input and type the value
        await locator.focus()
        await browser.page.keyboard.type(value, delay=50)
        await browser.page.wait_for_timeout(200)  # Debounce for filtering

        # Press Enter to select the filtered option
        await browser.page.keyboard.press("Enter")
        await browser.page.wait_for_timeout(300)  # Wait for selection

        # Verify selection (check if dropdown closed)
        aria_expanded = await element_handle.get_attribute("aria-expanded")
        if aria_expanded == "false":
            print(f"[SALESFORCE] ✅ Selected '{value}' via type-ahead")
            return True

        print(f"[SALESFORCE] ⚠️ Type-ahead didn't work, trying next strategy...")
    except Exception as e:
        print(f"[SALESFORCE] ⚠️ Type-ahead failed: {e}")

    # STRATEGY 2: aria-controls listbox targeting (scoped search)
    # Targets specific listbox, not global page elements
    try:
        print(f"[SALESFORCE] 🎯 Strategy 2: aria-controls listbox targeting")
        await locator.click(timeout=5000)
        await browser.page.wait_for_load_state("domcontentloaded")
        await browser.page.wait_for_timeout(500)

        # Get the listbox ID from aria-controls
        aria_controls = await element_handle.get_attribute("aria-controls")

        if aria_controls:
            print(f"[SALESFORCE] 📍 Targeting listbox: #{aria_controls}")

            # Target the specific listbox (may be portaled to body)
            listbox = browser.page.locator(f"#{aria_controls}")

            # Wait for listbox to be visible
            try:
                await listbox.wait_for(state="visible", timeout=2000)
            except Exception:
                print(f"[SALESFORCE] ⚠️ Listbox #{aria_controls} not visible")
                raise

            # Try multiple role patterns (Lightning uses different roles)
            role_patterns = [
                ("option", "role=option"),
                ("menuitemradio", "role=menuitemradio"),
                ("listitem", "li.slds-listbox__item"),
                ("class", ".slds-listbox__option"),
            ]

            for role_name, selector_pattern in role_patterns:
                try:
                    # Search within the specific listbox
                    if role_name in ["option", "menuitemradio"]:
                        options = listbox.get_by_role(role_name)
                    else:
                        options = listbox.locator(selector_pattern)

                    option_count = await options.count()

                    if option_count > 0:
                        print(f"[SALESFORCE] 🔍 Found {option_count} items with {role_name}")

                        # Search for matching value
                        for i in range(option_count):
                            opt = options.nth(i)
                            opt_text = (await opt.inner_text()).strip()

                            if value.lower() in opt_text.lower():
                                print(f"[SALESFORCE] ✅ Found '{value}' at index {i}, clicking...")
                                await opt.click(timeout=5000)
                                print(f"[SALESFORCE] ✅ Selected '{value}' via {role_name}")
                                return True
                except Exception:
                    continue

            print(f"[SALESFORCE] ⚠️ aria-controls targeting didn't find option")
        else:
            print(f"[SALESFORCE] ⚠️ No aria-controls attribute found")

    except Exception as e:
        print(f"[SALESFORCE] ⚠️ aria-controls targeting failed: {e}")

    # STRATEGY 3: Keyboard navigation (rock-solid fallback)
    # Sidesteps DOM role inconsistencies entirely
    try:
        print(f"[SALESFORCE] 🎯 Strategy 3: Keyboard navigation")
        await locator.click(timeout=5000)
        await browser.page.wait_for_timeout(500)

        # Arrow down through options, reading highlighted text
        max_attempts = 20  # Prevent infinite loops
        for attempt in range(max_attempts):
            await browser.page.keyboard.press("ArrowDown")
            await browser.page.wait_for_timeout(150)

            # Read the currently highlighted option (Lightning updates aria-activedescendant)
            try:
                active_descendant = await element_handle.get_attribute("aria-activedescendant")
                if active_descendant:
                    active_option = browser.page.locator(f"#{active_descendant}")
                    highlighted_text = (await active_option.inner_text()).strip()

                    if value.lower() in highlighted_text.lower():
                        print(f"[SALESFORCE] ✅ Found '{value}' at position {attempt}, pressing Enter")
                        await browser.page.keyboard.press("Enter")
                        await browser.page.wait_for_timeout(300)
                        print(f"[SALESFORCE] ✅ Selected '{value}' via keyboard nav")
                        return True
            except Exception:
                continue

        print(f"[SALESFORCE] ⚠️ Keyboard nav exhausted after {max_attempts} attempts")

    except Exception as e:
        print(f"[SALESFORCE] ⚠️ Keyboard navigation failed: {e}")

    # All strategies failed
    print(f"[SALESFORCE] ❌ All strategies failed for '{value}'")
    return False


def is_launcher_search(selector: str) -> bool:
    """Check if selector is a Salesforce App Launcher search pattern."""
    return selector and selector.startswith("LAUNCHER_SEARCH:")


def extract_launcher_target(selector: str) -> str:
    """Extract target name from LAUNCHER_SEARCH:target selector."""
    return selector.split(":", 1)[1] if is_launcher_search(selector) else ""


# Lightning readiness detection (Day 9 - fixes timing issues)
LIGHTNING_HOST_RE = re.compile(r"(?:\.lightning\.force\.com|\.my\.salesforce\.com)$", re.I)


def is_lightning(url_or_host: str) -> bool:
    """
    Check if URL or hostname is a Salesforce Lightning domain.

    Args:
        url_or_host: Full URL or just hostname

    Returns:
        bool: True if Lightning domain detected
    """
    host = url_or_host or ""
    return bool(LIGHTNING_HOST_RE.search(host))


def is_lightning_form_url(url: str) -> bool:
    """
    Check if URL is a Lightning form creation page (list → new).

    Phase 2a (Week 3): Used for optional cache bypass to avoid
    within-session ID volatility on form pages.

    Args:
        url: Full URL to check

    Returns:
        bool: True if Lightning form create page detected

    Examples:
        >>> is_lightning_form_url("https://org.lightning.force.com/lightning/o/Opportunity/new")
        True
        >>> is_lightning_form_url("https://org.lightning.force.com/lightning/o/Opportunity/list")
        False
    """
    if not url:
        return False
    u = url.lower()
    # List → form create pages pattern
    return ("lightning.force.com" in u or ".my.salesforce.com" in u) and ("/lightning/" in u) and ("/new" in u)


async def ensure_lightning_ready(page) -> None:
    """
    Wait for Lightning SPA to fully hydrate before discovery.

    Addresses Day 9 finding: Lightning requires 1-2 seconds to settle
    after navigation, causing timeouts when cache invalidation triggers
    re-discovery on partially-loaded pages.

    Strategy:
    1. Wait for DOM content loaded (basic structure)
    2. Wait for network idle (soft-fail if polling continues)
    3. Add empirical 1500ms settling time

    Args:
        page: Playwright page instance
    """
    print("[SALESFORCE] ⏳ Waiting for Lightning SPA to hydrate...")
    await page.wait_for_load_state("domcontentloaded")
    try:
        # Lightning often keeps polling; 5s timeout prevents infinite wait
        await page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass  # Soft-fail on polling/background requests

    # Empirical delay - fixes "New" button timeout (Day 9 test validation)
    await page.wait_for_timeout(1500)
    print("[SALESFORCE] ✅ Lightning ready")


async def resolve_combobox_by_label(page, label_text: str) -> Optional[str]:
    """
    Resolve Lightning combobox selector by aria-label when dynamic IDs fail.

    Week 3 patch: Lightning comboboxes use #combobox-button-NNN IDs that change
    across sessions. This fallback finds them via aria-label, role, or proximity.

    Args:
        page: Playwright page instance
        label_text: The label text to search for (e.g., "Stage", "Lead Source")

    Returns:
        Selector string if found, None otherwise

    Strategy score: 0.90 (tagged as sf_aria_combobox)
    """
    print(f"[SALESFORCE] 🔍 Combobox fallback for: '{label_text}'")

    # Strategy 1: aria-label match on button with listbox
    sel = f'button[role="button"][aria-haspopup="listbox"][aria-label*="{label_text}" i]'
    try:
        if await page.locator(sel).first.is_visible(timeout=2000):
            print(f"[SALESFORCE] ✅ Found via aria-label: {sel}")
            return sel
    except Exception:
        pass

    # Strategy 2: role=combobox with aria-label
    sel = f'[role="combobox"][aria-label*="{label_text}" i]'
    try:
        if await page.locator(sel).first.is_visible(timeout=2000):
            print(f"[SALESFORCE] ✅ Found via role=combobox: {sel}")
            return sel
    except Exception:
        pass

    # Strategy 3: Label proximity → nearest combobox/button
    try:
        label = page.get_by_label(label_text, exact=False)
        if await label.count() > 0:
            # Try parent chain for nearby combobox
            near_combo = label.locator('..').locator('[role="combobox"],button[aria-haspopup="listbox"]')
            if await near_combo.first.is_visible(timeout=2000):
                found_sel = await near_combo.first.evaluate("el => el.getAttribute('id') ? `#${el.id}` : el.tagName.toLowerCase()")
                print(f"[SALESFORCE] ✅ Found via label proximity: {found_sel}")
                return found_sel
    except Exception:
        pass

    # Strategy 4: Last resort - title attribute
    sel = f'button[title*="{label_text}" i][aria-haspopup="listbox"]'
    try:
        if await page.locator(sel).first.is_visible(timeout=2000):
            print(f"[SALESFORCE] ✅ Found via title: {sel}")
            return sel
    except Exception:
        pass

    print(f"[SALESFORCE] ❌ Combobox fallback exhausted for: '{label_text}'")
    return None


# Week 4: Stable selector builders (label-first discovery)
def build_input_selector_from_attrs(attrs: dict) -> Optional[str]:
    """
    Build stable input selector from attributes.
    Week 4: Priority - aria-label > name > placeholder (avoid volatile IDs).

    Args:
        attrs: Dictionary of element attributes

    Returns:
        Stable selector string or None
    """
    # Priority 1: aria-label (most stable)
    if al := attrs.get("aria-label"):
        return f'input[aria-label="{al}"]'

    # Priority 2: name attribute
    if nm := attrs.get("name"):
        return f'input[name="{nm}"]'

    # Priority 3: placeholder
    if ph := attrs.get("placeholder"):
        return f'input[placeholder="{ph}"]'

    return None


def build_combobox_button_selector(attrs: dict) -> Optional[str]:
    """
    Build stable combobox button selector from attributes.
    Week 4: Salesforce Lightning often exposes aria-label on buttons.

    Args:
        attrs: Dictionary of element attributes

    Returns:
        Stable selector string or None
    """
    # Priority 1: aria-label on button
    if al := attrs.get("aria-label"):
        return f'button[aria-label="{al}"]'

    # Priority 2: name attribute (fallback)
    if nm := attrs.get("name"):
        return f'role=button[name="{nm}"]'

    return None
