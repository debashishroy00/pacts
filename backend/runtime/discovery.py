from __future__ import annotations
from typing import Dict, Any, Optional
import re
import logging
from backend.mcp.mcp_client import get_playwright_client, USE_MCP

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """
    Normalize text for fuzzy matching.

    - Lowercase
    - Strip whitespace
    - Remove common suffixes (button, icon, link)
    - Remove extra spaces
    - Simplify special characters for matching
    """
    if not text:
        return ""

    # Lowercase and strip
    normalized = text.lower().strip()

    # Remove common UI element suffixes that LLMs add
    suffixes_to_remove = [
        ' button', ' icon', ' link', ' field', ' input',
        ' dropdown', ' menu', ' tab', ' checkbox', ' radio'
    ]

    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()

    # Simplify special characters that LLMs might omit
    # "Zip/Postal Code" → "zip postal code" (remove slash for matching)
    # This allows "Zip Code" to match "Zip/Postal Code"
    normalized = normalized.replace('/', ' ')  # Remove slashes
    normalized = normalized.replace('-', ' ')  # Remove hyphens

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized

def create_fuzzy_pattern(text: str) -> re.Pattern:
    """
    Create a regex pattern for fuzzy matching.

    Matches text with:
    - Optional whitespace
    - Optional common suffixes
    - Optional extra words (for "Zip Code" → "Zip/Postal Code")
    - Case insensitive

    Example: "Login" matches "Login", "login", "  Login  ", "Login Button"
    Example: "Zip Code" matches "Zip/Postal Code", "Zip Code", "zip code"
    """
    normalized = normalize_text(text)

    # Escape special regex characters in the core text
    escaped = re.escape(normalized)

    # Split normalized into words to allow partial matching
    words = normalized.split()

    if len(words) > 1:
        # Multi-word target: allow extra words between
        # "zip code" matches "zip postal code" or "zip/postal code"
        word_pattern = r'\s*[/\-]?\s*'.join(re.escape(w) for w in words)
        # Allow optional extra words between: "zip.*code"
        partial_pattern = r'\s*'.join(re.escape(w) + r'(?:\s*[/\-]?\s*\w+)?' for w in words[:-1]) + r'\s*' + re.escape(words[-1])
        pattern = rf'\s*(?:{word_pattern}|{partial_pattern})\s*(?:button|icon|link|field|input|dropdown|menu)?'
    else:
        # Single word: simpler pattern
        pattern = rf'\s*{escaped}\s*(?:button|icon|link|field|input|dropdown|menu)?'

    return re.compile(pattern, re.IGNORECASE)

STRATEGIES = [
    "label",
    "placeholder",
    "role_name",
    "relational_css",
    "shadow_pierce",
    "fallback_css",
]

ROLE_HINTS = {
    "login": "button",
    "submit": "button",
    "sign in": "button",
    "sign-in": "button",
    "sign_in": "button",
    "continue": "button",
    "next": "button",
    "ok": "button",
    "search": "button",
    "menu": "button",
    "tab": "tab",
    "link": "link",
    "button": "button",
}

async def _check_visibility(browser, selector, element) -> bool:
    """
    Check if element is visible.

    This is called during discovery to filter out hidden elements.
    Hidden elements are skipped so next strategy can try.
    """
    try:
        if element and hasattr(element, 'is_visible'):
            return await element.is_visible()
        # Fallback: query and check
        el = await browser.query(selector)
        if el:
            return await el.is_visible()
        return False
    except Exception:
        # If we can't check, assume not visible
        return False


async def _is_fillable_element(browser, selector, element, action: str = "fill") -> bool:
    """
    Check if element is appropriate for the requested action.

    For fill actions: prefer input/textarea, skip select/button
    For click actions: any element is fine
    """
    if action != "fill":
        return True  # Click actions can target any element

    try:
        if element:
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
        else:
            el = await browser.query(selector)
            if not el:
                return False
            tag_name = await el.evaluate("el => el.tagName.toLowerCase()")

        # For fill actions, skip select dropdowns and buttons
        # These need click, not fill
        if tag_name in ['select', 'button']:
            logger.debug(f"[Discovery] Skipping {tag_name} element for fill action: {selector}")
            return False

        return True
    except Exception:
        return True  # If we can't determine, allow it


async def _try_label(browser, intent) -> Optional[Dict[str, Any]]:
    name = intent.get("element") or intent.get("label") or intent.get("intent")
    if not name:
        return None

    normalized_name = normalize_text(name)
    action = intent.get("action", "fill")

    # Try exact match first
    exact_pattern = re.compile(re.escape(normalized_name), re.I)
    found = await browser.find_by_label(exact_pattern)
    if found:
        selector, el = found
        # Check visibility - skip hidden elements
        if not await _check_visibility(browser, selector, el):
            logger.debug(f"[Discovery] Label match '{selector}' is hidden, trying next strategy")
            return None
        # Check if element is appropriate for action (skip select for fill)
        if not await _is_fillable_element(browser, selector, el, action):
            logger.debug(f"[Discovery] Label match '{selector}' is not fillable (likely select/button), trying next strategy")
            return None
        return {"selector": selector, "score": 0.92, "meta": {"strategy": "label", "name": name, "normalized": normalized_name}}

    # Try fuzzy match
    fuzzy_pattern = create_fuzzy_pattern(normalized_name)
    found = await browser.find_by_label(fuzzy_pattern)
    if found:
        selector, el = found
        # Check visibility - skip hidden elements
        if not await _check_visibility(browser, selector, el):
            logger.debug(f"[Discovery] Label fuzzy match '{selector}' is hidden, trying next strategy")
            return None
        # Check if element is appropriate for action
        if not await _is_fillable_element(browser, selector, el, action):
            logger.debug(f"[Discovery] Label fuzzy match '{selector}' is not fillable, trying next strategy")
            return None
        return {"selector": selector, "score": 0.90, "meta": {"strategy": "label_fuzzy", "name": name, "normalized": normalized_name}}

    return None

async def _try_placeholder(browser, intent) -> Optional[Dict[str, Any]]:
    name = intent.get("element") or intent.get("placeholder") or intent.get("intent")
    if not name:
        return None

    normalized_name = normalize_text(name)

    # Try exact match first
    exact_pattern = re.compile(re.escape(normalized_name), re.I)
    found = await browser.find_by_placeholder(exact_pattern)
    if found:
        selector, el = found
        # Check visibility - skip hidden elements
        if not await _check_visibility(browser, selector, el):
            logger.debug(f"[Discovery] Placeholder match '{selector}' is hidden, trying next strategy")
            return None
        return {"selector": selector, "score": 0.88, "meta": {"strategy": "placeholder", "name": name, "normalized": normalized_name}}

    # Try fuzzy match
    fuzzy_pattern = create_fuzzy_pattern(normalized_name)
    found = await browser.find_by_placeholder(fuzzy_pattern)
    if found:
        selector, el = found
        # Check visibility - skip hidden elements
        if not await _check_visibility(browser, selector, el):
            logger.debug(f"[Discovery] Placeholder fuzzy match '{selector}' is hidden, trying next strategy")
            return None
        return {"selector": selector, "score": 0.86, "meta": {"strategy": "placeholder_fuzzy", "name": name, "normalized": normalized_name}}

    return None

async def _try_role_name(browser, intent) -> Optional[Dict[str, Any]]:
    name = (intent.get("element") or intent.get("intent") or "").strip()
    action = (intent.get("action") or "").lower()
    if not name:
        return None

    # Normalize the target name (remove "button", "icon" etc suffixes)
    normalized_name = normalize_text(name)

    # Determine role hint
    role = None
    # Prefer action mapping
    if action == "click":
        role = "button"
    # Keyword mapping (check normalized name for hints)
    for key, r in ROLE_HINTS.items():
        if key in normalized_name:
            role = r
            break

    # Final fallback: try common roles
    candidates = [role] if role else ["button", "link", "tab"]

    # Try exact match first (fastest)
    exact_pattern = re.compile(re.escape(normalized_name), re.I)
    for r in candidates:
        found = await browser.find_by_role(r, exact_pattern)
        if found:
            selector, el = found
            # Check visibility - skip hidden elements
            if not await _check_visibility(browser, selector, el):
                logger.debug(f"[Discovery] Role '{r}' match '{selector}' is hidden, trying next")
                continue  # Try next role candidate
            return {
                "selector": selector,
                "score": 0.95,
                "meta": {"strategy": "role_name", "role": r, "name": name, "normalized": normalized_name}
            }

    # Try fuzzy match (handles extra whitespace, capitalization)
    fuzzy_pattern = create_fuzzy_pattern(normalized_name)
    for r in candidates:
        found = await browser.find_by_role(r, fuzzy_pattern)
        if found:
            selector, el = found
            # Check visibility - skip hidden elements
            if not await _check_visibility(browser, selector, el):
                logger.debug(f"[Discovery] Role '{r}' fuzzy match '{selector}' is hidden, trying next")
                continue  # Try next role candidate
            return {
                "selector": selector,
                "score": 0.93,  # Slightly lower confidence for fuzzy match
                "meta": {"strategy": "role_name_fuzzy", "role": r, "name": name, "normalized": normalized_name}
            }

    return None

async def _try_relational_css(browser, intent) -> Optional[Dict[str, Any]]:
    """
    Find elements by relationship to nearby text/elements.

    Example: "Add to cart" button next to "Sauce Labs Backpack" product name
    Strategy: Find anchor text, then look for action element nearby
    """
    name = (intent.get("element") or intent.get("intent") or "").strip()
    value = (intent.get("value") or "").strip()  # Optional context/product name
    action = (intent.get("action") or "").lower()

    if not name:
        return None

    # Check two patterns:
    # Pattern 1: Combined name like "Sauce Labs Backpack Add to Cart"
    # Pattern 2: Separate name and value like name="Add to cart", value="Sauce Labs Backpack"

    action_keywords = ["add to cart", "remove", "delete", "edit", "view", "buy", "purchase", "select"]

    found_action = None
    context_text = None

    normalized_name = normalize_text(name)

    # First check if value field has context (Pattern 2 - preferred)
    if value:
        # Value contains product/item name, name contains action
        context_text = normalize_text(value)
        found_action = normalized_name
        logger.info(f"[Relational] Pattern2 - Context from value='{context_text}' Action from name='{found_action}'")
    else:
        # Check if name contains both context and action (Pattern 1 - fallback)
        for keyword in action_keywords:
            if keyword in normalized_name:
                # Split: everything before keyword = context, keyword = action
                parts = normalized_name.split(keyword, 1)
                if len(parts) == 2 and parts[0].strip():
                    context_text = parts[0].strip()
                    found_action = keyword.strip()
                    logger.info(f"[Relational] Pattern1 - Context='{context_text}' Action='{found_action}'")
                    break

    # If we found a context + action pattern, use relational discovery
    if context_text and found_action:
        logger.info(f"[Relational] Context='{context_text}' Action='{found_action}'")

        # Try to find button with action text that's near context text
        # This requires browser-side script execution
        # For now, try a simpler approach: look for unique combination in parent container

        # Strategy: Find the context text, then find the action button in same container
        try:
            # Use Playwright to find element containing context text
            context_locator = browser.page.locator(f"text=/{re.escape(context_text)}/i")
            context_count = await context_locator.count()

            if context_count > 0:
                # Found context text, now find the action button relative to it
                # Try: ancestor container with both context and action
                for idx in range(min(context_count, 5)):  # Check up to 5 matches
                    context_el = context_locator.nth(idx)

                    # Navigate up to parent container (product card, row, etc.)
                    parent = context_el.locator("xpath=ancestor::div[contains(@class, 'item') or contains(@class, 'product') or contains(@class, 'card') or contains(@class, 'row')][1]")

                    if await parent.count() == 0:
                        # No specific parent container, try direct parent
                        parent = context_el.locator("xpath=..")

                    # Within parent, find button with action text
                    action_button = parent.locator(f"button:has-text('{found_action}')")

                    if await action_button.count() == 0:
                        # Try normalized action (without spaces)
                        action_normalized = found_action.replace(" ", "-")
                        action_button = parent.locator(f"button[id*='{action_normalized}'], button[class*='{action_normalized}']")

                    if await action_button.count() > 0:
                        # Found it! Get the selector
                        handle = await action_button.first.element_handle()
                        if handle:
                            id_val = await handle.get_attribute('id')
                            if id_val:
                                return {
                                    "selector": f"#{id_val}",
                                    "score": 0.92,
                                    "meta": {
                                        "strategy": "relational_css",
                                        "context": context_text,
                                        "action": found_action,
                                        "name": name
                                    }
                                }

        except Exception as e:
            logger.warning(f"[Relational] Failed: {e}")

    return None

async def _try_shadow_pierce(browser, intent) -> Optional[Dict[str, Any]]:
    return None

async def _try_fallback_css(browser, intent) -> Optional[Dict[str, Any]]:
    return None

STRATEGY_FUNCS = {
    "label": _try_label,
    "placeholder": _try_placeholder,
    "role_name": _try_role_name,
    "relational_css": _try_relational_css,
    "shadow_pierce": _try_shadow_pierce,
    "fallback_css": _try_fallback_css,
}

async def discover_selector(browser, intent) -> Optional[Dict[str, Any]]:
    """
    Discover selector for an intent using multiple strategies with priority order:

    0. MCP Playwright (if enabled and available) - Highest priority
    1. Explicit prefixes (css:, role:) - User override
    2. Semantic strategies (role_name, label, placeholder)
    3. Heuristics for common landmarks (Cart, Checkout)
    4. Fallback strategies (relational_css, shadow_pierce, fallback_css)
    """
    target = (intent.get("element") or intent.get("target") or intent.get("intent") or "").strip()
    within = intent.get("within")  # Region scope hint (e.g., "App Launcher")
    # DEBUG: Log intent to see what is being passed
    element = intent.get("element")
    target_val = intent.get("target")
    logger.info(f"[Discovery] Intent received: element={element} target={target_val} within={within}")

    # PRIORITY 0: Dialog-scoped discovery for Salesforce App Launcher (immediate fix)
    if within:
        logger.info(f"[Discovery] Region-scoped discovery: target='{target}' within='{within}'")

        try:
            # Salesforce App Launcher: Use dialog-scoped locators
            if "app launcher" in within.lower():
                # Find the App Launcher dialog
                panel = browser.page.get_by_role("dialog", name=re.compile("app.?launcher", re.I))
                panel_count = await panel.count()

                if panel_count > 0:
                    logger.info(f"[Discovery] Found App Launcher dialog, using scoped search")

                    # Try robust launcher search first (works across all orgs)
                    target_lower = target.lower()
                    if target_lower in ["accounts", "contacts", "leads", "opportunities", "cases"]:
                        # Use search box in launcher
                        search = panel.get_by_role("combobox", name=re.compile("search", re.I)).first
                        search_count = await search.count()

                        if search_count > 0:
                            logger.info(f"[Discovery] Using launcher search for '{target}'")
                            # Return special selector that triggers launcher search in executor
                            return {
                                "selector": f"LAUNCHER_SEARCH:{target}",
                                "score": 0.98,
                                "meta": {
                                    "strategy": "launcher_search",
                                    "region": within,
                                    "target": target,
                                    "method": "search"
                                }
                            }

                    # Fallback: Direct button/link click within dialog
                    # Try button first
                    scoped_button = panel.get_by_role("button", name=re.compile(f"^{re.escape(target)}$", re.I))
                    button_count = await scoped_button.count()

                    if button_count > 0:
                        logger.info(f"[Discovery] Found {button_count} button(s) for '{target}' in App Launcher")
                        # Generate selector scoped to dialog
                        return {
                            "selector": f'role=dialog[name*="app launcher" i] >> role=button[name="{target}" i]',
                            "score": 0.97,
                            "meta": {
                                "strategy": "dialog_scoped_button",
                                "region": within,
                                "count": button_count
                            }
                        }

                    # Try link (some orgs use links instead of buttons)
                    scoped_link = panel.get_by_role("link", name=re.compile(f"^{re.escape(target)}$", re.I))
                    link_count = await scoped_link.count()

                    if link_count > 0:
                        logger.info(f"[Discovery] Found {link_count} link(s) for '{target}' in App Launcher")
                        return {
                            "selector": f'role=dialog[name*="app launcher" i] >> role=link[name="{target}" i]',
                            "score": 0.97,
                            "meta": {
                                "strategy": "dialog_scoped_link",
                                "region": within,
                                "count": link_count
                            }
                        }

        except Exception as e:
            logger.warning(f"[Discovery] Dialog-scoped discovery failed: {e}, falling back...")

    # PRIORITY 1: MCP Direct Action Tools (Phase 1 - NEW!)
    # Use MCP to discover AND perform action in one step
    # Handles Shadow DOM, React, complex SPAs automatically
    if USE_MCP:
        try:
            from backend.mcp.mcp_client import discover_and_act_via_mcp
            mcp_action_result = await discover_and_act_via_mcp(intent)
            if mcp_action_result:
                # MCP successfully performed the action
                # Return special MCP_* selector for executor to recognize
                logger.info(f"[Discovery] MCP direct action succeeded: {mcp_action_result.get('selector')}")
                return mcp_action_result
        except Exception as e:
            logger.warning(f"[Discovery] MCP direct action failed: {e}, trying fallback...")

    # PRIORITY 2: MCP Snapshot Discovery (legacy - keep for compatibility)
    if USE_MCP:
        try:
            from backend.mcp.mcp_client import discover_locator_via_mcp
            mcp_result = await discover_locator_via_mcp(intent)
            if mcp_result and mcp_result.get("selector"):
                # MCP found a complete selector
                logger.info(f"MCP discovered selector for '{target}': {mcp_result.get('selector')}")
                return mcp_result
            elif mcp_result:
                # MCP confirmed element exists but didn't provide selector
                # Continue to local strategies with confidence boost
                logger.info(f"MCP confirmed '{target}' exists in accessibility tree")
        except Exception as e:
            logger.warning(f"MCP discovery failed, falling back to local: {e}")
            # Fall through to local strategies

    # PRIORITY 1: Explicit CSS override (css:.shopping_cart_link)
    if target.startswith("css:"):
        selector = target[4:].strip()  # Remove "css:" prefix
        # Verify selector exists
        count = await browser.locator_count(selector)
        if count > 0:
            return {
                "selector": selector,
                "score": 0.99,
                "meta": {"strategy": "css_override", "explicit": True}
            }
        return None

    # PRIORITY 2: Explicit role override (role:button=Login or role:link=Cart)
    if target.startswith("role:"):
        role_spec = target[5:].strip()
        if "=" in role_spec:
            role, _, name = role_spec.partition("=")
            role = role.strip()
            name = name.strip()

            # Use Playwright's get_by_role
            try:
                loc = browser.page.get_by_role(role, name=re.compile(re.escape(name), re.I))
                count = await loc.count()
                if count > 0:
                    # Generate stable selector (prefer ID, then data-test, then role)
                    el = await loc.first.element_handle()
                    selector_id = await el.get_attribute("id")
                    if selector_id:
                        selector = f"#{selector_id}"
                    else:
                        # Fallback to role-based selector
                        selector = f'[role="{role}"]'

                    return {
                        "selector": selector,
                        "score": 0.98,
                        "meta": {"strategy": "role_override", "role": role, "name": name, "explicit": True}
                    }
            except Exception:
                pass
        return None

    # PRIORITY 3: Semantic strategies (existing)
    for name in STRATEGIES[:3]:  # label, placeholder, role_name
        cand = await STRATEGY_FUNCS[name](browser, intent)
        if cand:
            return cand

    # PRIORITY 4: Heuristics for common landmarks
    target_lower = target.lower()

    # Cart/Shopping Cart heuristic
    if target_lower in {"cart", "shopping cart", "basket", "shopping_cart"}:
        # Try common cart selectors
        for cart_sel in [".shopping_cart_link", "a.shopping_cart_link", "[data-test='shopping-cart-link']", "#shopping_cart_container a"]:
            count = await browser.locator_count(cart_sel)
            if count > 0:
                return {
                    "selector": cart_sel,
                    "score": 0.90,
                    "meta": {"strategy": "heuristic", "hint": "cart_link"}
                }

    # Checkout heuristic
    if target_lower in {"checkout", "proceed to checkout", "check out"}:
        # Try role-based checkout button first
        try:
            loc = browser.page.get_by_role("button", name=re.compile(r"checkout", re.I))
            count = await loc.count()
            if count > 0:
                el = await loc.first.element_handle()
                selector_id = await el.get_attribute("id")
                if selector_id:
                    selector = f"#{selector_id}"
                else:
                    selector = "button:has-text('Checkout')"

                return {
                    "selector": selector,
                    "score": 0.90,
                    "meta": {"strategy": "heuristic", "hint": "checkout_button"}
                }
        except Exception:
            pass

    # PRIORITY 5: Fallback strategies (currently stubs)
    for name in STRATEGIES[3:]:  # relational_css, shadow_pierce, fallback_css
        cand = await STRATEGY_FUNCS[name](browser, intent)
        if cand:
            return cand

    return None


# ==========================================
# ORACLE HEALER V2: REPROBE WITH ALTERNATES
# ==========================================

async def reprobe_with_alternates(
    browser,
    intent: Dict[str, Any],
    heal_round: int = 0,
    hints: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Re-discover selector using alternate strategies (healing mode).

    Priority:
        0. MCP Playwright reprobe (if enabled) - Uses fallback chain
        1. role_name with relaxed matching (Round 1)
        2. label → placeholder fallbacks (Round 2)
        3. fallback_css heuristics + last_known_good cache (Round 3)

    Args:
        browser: BrowserClient instance
        intent: Original intent dict (element, action, value, region)
        heal_round: Current healing round (1-3)
        hints: Optional cache hints {last_known_good: {element: selector}}

    Returns:
        Discovered selector dict with confidence, or None if all strategies fail
    """
    hints = hints or {}
    last_known_good = hints.get("last_known_good", {})
    element_name = intent.get("element") or intent.get("target") or intent.get("intent", "")

    # PRIORITY 0: MCP Playwright reprobe (if enabled)
    if USE_MCP:
        try:
            from backend.mcp.mcp_client import discover_locator_via_mcp
            # For reprobe, we use the same discovery but with lower confidence
            mcp_result = await discover_locator_via_mcp(intent)
            if mcp_result:
                logger.info(f"MCP reprobe for '{element_name}' (round {heal_round}): {mcp_result.get('selector')}")
                # Adjust confidence for reprobe
                mcp_result["score"] = mcp_result.get("score", 0.85) * 0.9  # Slightly lower for reprobe
                mcp_result["meta"]["heal_round"] = heal_round
                return mcp_result
        except Exception as e:
            logger.warning(f"MCP reprobe failed, falling back to local: {e}")
            # Fall through to local strategies

    # Round 1: Relaxed role_name (case-insensitive, regex)
    if heal_round >= 1:
        result = await _try_role_name_relaxed(browser, intent)
        if result:
            return result

    # Round 2: Fallback to label/placeholder (even if original strategy was role_name)
    if heal_round >= 2:
        # Try label strategy
        result = await _try_label(browser, intent)
        if result:
            return result

        # Try placeholder strategy
        result = await _try_placeholder(browser, intent)
        if result:
            return result

    # Round 3: Last resort strategies
    if heal_round >= 3:
        # Check last_known_good cache
        if element_name in last_known_good:
            cached_selector = last_known_good[element_name]
            try:
                el = await browser.query(cached_selector)
                if el:
                    return {
                        "selector": cached_selector,
                        "score": 0.70,  # Lower confidence (cached)
                        "meta": {"strategy": "last_known_good", "name": element_name}
                    }
            except Exception:
                pass

        # Fallback CSS heuristics
        result = await _try_fallback_css_heuristics(browser, intent)
        if result:
            return result

    # All strategies exhausted
    return None


async def _try_role_name_relaxed(browser, intent) -> Optional[Dict[str, Any]]:
    """Relaxed role_name: case-insensitive regex matching."""
    name = (intent.get("element") or intent.get("intent") or "").strip()
    action = (intent.get("action") or "").lower()
    if not name:
        return None

    # Determine role hint
    role = None
    if action == "click":
        role = "button"
    for key, r in ROLE_HINTS.items():
        if key in name.lower():
            role = r
            break

    candidates = [role] if role else ["button", "link", "tab"]

    # Relaxed regex: case-insensitive, partial match
    import re
    pat = re.compile(f".*{re.escape(name)}.*", re.I)

    for r in candidates:
        found = await browser.find_by_role(r, pat)
        if found:
            selector, el = found
            return {
                "selector": selector,
                "score": 0.85,  # Lower confidence (relaxed)
                "meta": {"strategy": "role_name_relaxed", "role": r, "name": name}
            }
    return None


async def _try_fallback_css_heuristics(browser, intent) -> Optional[Dict[str, Any]]:
    """Fallback CSS heuristics for common button/input patterns."""
    name = (intent.get("element") or intent.get("intent") or "").strip().lower()
    action = (intent.get("action") or "").lower()

    # Heuristic selectors for common patterns
    heuristics = []

    if action == "click":
        heuristics.extend([
            f'button:has-text("{name}")',
            f'[type="submit"]:has-text("{name}")',
            f'a:has-text("{name}")',
            f'[data-test*="{name}"]',
            f'[data-testid*="{name}"]',
            f'.btn:has-text("{name}")',
        ])
    elif action == "fill":
        heuristics.extend([
            f'input[name*="{name}"]',
            f'input[id*="{name}"]',
            f'textarea[name*="{name}"]',
            f'[data-test*="{name}"]',
        ])

    # Try each heuristic
    for selector in heuristics:
        try:
            count = await browser.locator_count(selector)
            if count > 0:
                el = await browser.query(selector)
                if el:
                    return {
                        "selector": selector,
                        "score": 0.70,  # Lower confidence (heuristic)
                        "meta": {"strategy": "fallback_css", "name": name}
                    }
        except Exception:
            continue

    return None
