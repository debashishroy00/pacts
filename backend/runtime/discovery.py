from __future__ import annotations
from typing import Dict, Any, Optional
import re
import logging
from backend.mcp.playwright_client import get_client, USE_MCP

logger = logging.getLogger(__name__)

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

async def _try_label(browser, intent) -> Optional[Dict[str, Any]]:
    name = intent.get("element") or intent.get("label") or intent.get("intent")
    if not name:
        return None
    pat = re.compile(re.escape(name), re.I)
    found = await browser.find_by_label(pat)
    if not found:
        return None
    selector, el = found
    return {"selector": selector, "score": 0.92, "meta": {"strategy": "label", "name": name}}

async def _try_placeholder(browser, intent) -> Optional[Dict[str, Any]]:
    name = intent.get("element") or intent.get("placeholder") or intent.get("intent")
    if not name:
        return None
    pat = re.compile(re.escape(name), re.I)
    found = await browser.find_by_placeholder(pat)
    if not found:
        return None
    selector, el = found
    return {"selector": selector, "score": 0.88, "meta": {"strategy": "placeholder", "name": name}}

async def _try_role_name(browser, intent) -> Optional[Dict[str, Any]]:
    name = (intent.get("element") or intent.get("intent") or "").strip()
    action = (intent.get("action") or "").lower()
    if not name:
        return None
    # Determine role hint
    role = None
    # Prefer action mapping
    if action == "click":
        role = "button"
    # Keyword mapping
    for key, r in ROLE_HINTS.items():
        if key in name.lower():
            role = r
            break
    # Final fallback: try common roles
    candidates = [role] if role else ["button", "link", "tab"]
    pat = re.compile(re.escape(name), re.I)
    for r in candidates:
        found = await browser.find_by_role(r, pat)
        if found:
            selector, el = found
            return {
                "selector": selector,
                "score": 0.95,
                "meta": {"strategy": "role_name", "role": r, "name": name}
            }
    return None

async def _try_relational_css(browser, intent) -> Optional[Dict[str, Any]]:
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

    # PRIORITY 0: MCP Playwright discovery (if enabled)
    if USE_MCP:
        try:
            mcp_client = get_client()
            mcp_result = await mcp_client.discover_locator(intent)
            if mcp_result:
                logger.info(f"MCP discovered selector for '{target}': {mcp_result.get('selector')} (strategy: {mcp_result.get('strategy')})")
                # Convert MCP result to our format
                return {
                    "selector": mcp_result["selector"],
                    "score": mcp_result.get("confidence", 0.95),
                    "meta": {
                        "strategy": f"mcp_{mcp_result.get('strategy', 'unknown')}",
                        "channel": "mcp",
                        "notes": mcp_result.get("notes", "")
                    }
                }
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
            mcp_client = get_client()
            mcp_result = await mcp_client.reprobe(element_name, heal_round)
            if mcp_result:
                logger.info(f"MCP reprobe for '{element_name}' (round {heal_round}): {mcp_result.get('selector')} via {mcp_result.get('strategy')}")
                return {
                    "selector": mcp_result["selector"],
                    "score": mcp_result.get("confidence", 0.85),
                    "meta": {
                        "strategy": f"mcp_reprobe_{mcp_result.get('strategy', 'unknown')}",
                        "channel": "mcp",
                        "fallback_chain": mcp_result.get("fallback_chain", []),
                        "heal_round": heal_round
                    }
                }
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
