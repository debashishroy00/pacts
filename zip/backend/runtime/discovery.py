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
