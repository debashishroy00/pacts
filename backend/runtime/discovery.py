from __future__ import annotations
from typing import Dict, Any, Optional
import re

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
    for name in STRATEGIES:
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

    Strategy Ladder (based on heal_round):
        Round 1: role_name with relaxed matching
        Round 2: label → placeholder fallbacks
        Round 3: fallback_css heuristics + last_known_good cache

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
    element_name = intent.get("element") or intent.get("intent", "")

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
