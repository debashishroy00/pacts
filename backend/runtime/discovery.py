from __future__ import annotations
from typing import Dict, Any, Optional
import re
import logging
import os
from backend.mcp.mcp_client import get_playwright_client, USE_MCP
from backend.runtime.salesforce_helpers import ensure_lightning_ready_list, resolve_scope_container
from backend.utils import ulog  # Week 8 EDR: Unified structured logging

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
    - Optional common suffixes (button, field, input, etc.)
    - Optional extra words (for "Zip Code" → "Zip/Postal Code")
    - Rejects UI control suffixes (width, height, column, etc.)
    - Case insensitive

    Example: "Login" matches "Login", "login", "  Login  ", "Login Button"
    Example: "Close Date" matches "Close Date Field" but NOT "Close Date column width"
    """
    normalized = normalize_text(text)

    # Escape special regex characters in the core text
    escaped = re.escape(normalized)

    # Split normalized into words to allow partial matching
    words = normalized.split()

    # Allowed suffixes for form fields (whitelist approach)
    ALLOWED_SUFFIXES = r'(?:button|icon|link|field|input|dropdown|menu|box|selector)?'

    if len(words) > 1:
        # Multi-word target: allow extra words between
        # "zip code" matches "zip postal code" or "zip/postal code"
        word_pattern = r'\s*[/\-]?\s*'.join(re.escape(w) for w in words)
        # Allow optional extra words between: "zip.*code"
        partial_pattern = r'\s*'.join(re.escape(w) + r'(?:\s*[/\-]?\s*\w+)?' for w in words[:-1]) + r'\s*' + re.escape(words[-1])
        pattern = rf'\s*(?:{word_pattern}|{partial_pattern})\s*{ALLOWED_SUFFIXES}$'
    else:
        # Single word: simpler pattern
        pattern = rf'\s*{escaped}\s*{ALLOWED_SUFFIXES}$'

    return re.compile(pattern, re.IGNORECASE)

# Week 8 EDR: Universal Discovery Order (8-tier stability-first hierarchy)
# Priority: Stable selectors (1-5, 7) → Volatile selectors (6, 8)
STRATEGIES = [
    "aria_label",         # Tier 1: aria-label, aria-labelledby (✅ Stable)
    "aria_placeholder",   # Tier 2: aria-placeholder (✅ Stable)
    "name_attr",          # Tier 3: name attribute (✅ Stable)
    "placeholder_attr",   # Tier 4: placeholder attribute (✅ Stable)
    "label_for",          # Tier 5: <label for> proximity (✅ Stable)
    "role_name",          # Tier 6: Visible text / role-name (⚠ Volatile)
    "data_attr",          # Tier 7: data-* attribute (✅ Stable)
    "id_class",           # Tier 8: id / class (⚠ Volatile - last resort)
    # Phase 4a: Site-specific strategies (before legacy fallbacks)
    "youtube_video",      # YouTube video result detection
    "reddit_search",      # Reddit search box detection
    "booking_destination",  # Booking.com destination field
    "booking_autocomplete",  # Booking.com autocomplete dropdown
    # Legacy strategies (backwards compatibility)
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
    "search": "searchbox",  # Phase 4a: searchbox role for search inputs
    "menu": "button",
    "video": "link",  # Phase 4a: YouTube video results
    "result": "link",  # Phase 4a: Generic result links
    "first": "link",  # Phase 4a: First result pattern
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

    For fill actions: prefer input/textarea, skip select/button/slider/color/range
    For click actions: any element is fine
    """
    if action != "fill":
        return True  # Click actions can target any element

    try:
        if element:
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            input_type = await element.evaluate("el => el.type ? el.type.toLowerCase() : null")
        else:
            el = await browser.query(selector)
            if not el:
                return False
            tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
            input_type = await el.evaluate("el => el.type ? el.type.toLowerCase() : null")

        # For fill actions, skip non-fillable elements
        if tag_name in ['select', 'button']:
            logger.debug(f"[Discovery] Skipping {tag_name} element for fill action: {selector}")
            return False

        # Skip input controls that aren't text-fillable
        # range = sliders (column width adjusters, volume controls)
        # color = color pickers
        # file = file upload buttons
        # checkbox/radio = need click, not fill
        NON_FILLABLE_INPUT_TYPES = ['range', 'color', 'file', 'checkbox', 'radio', 'button', 'submit', 'reset', 'image']
        if tag_name == 'input' and input_type in NON_FILLABLE_INPUT_TYPES:
            logger.debug(f"[Discovery] Skipping input[type={input_type}] for fill action: {selector}")
            return False

        return True
    except Exception:
        return True  # If we can't determine, allow it


# ═══════════════════════════════════════════════════════════════════════════════
# Week 8 EDR: Universal Discovery Strategies (8-Tier Hierarchy)
# ═══════════════════════════════════════════════════════════════════════════════

async def _try_aria_label(browser, intent) -> Optional[Dict[str, Any]]:
    """
    Tier 1: aria-label, aria-labelledby (STABLE)

    Highest priority - semantic, accessible, framework-independent.
    Uses scoped discovery for complex UIs (Lightning, modals).
    """
    name = intent.get("element") or intent.get("label") or intent.get("intent")
    if not name:
        return None

    action = intent.get("action", "fill")
    within = intent.get("within")  # Scoped context

    # Try scoped discovery first for fill actions
    if action == "fill":
        try:
            from backend.runtime.scope_helpers import resolve_container, prefer_form_control_with_label

            scope = await resolve_container(browser.page, within)
            form_control = await prefer_form_control_with_label(name, scope)

            if form_control and await form_control.count() > 0:
                el = form_control.first
                tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                aria_label_val = await el.get_attribute("aria-label")
                name_val = await el.get_attribute("name")

                if aria_label_val:
                    refined_selector = f'{tag_name}[aria-label="{aria_label_val}"]'
                elif name_val:
                    refined_selector = f'{tag_name}[name="{name_val}"]'
                else:
                    labelledby = await el.get_attribute("aria-labelledby")
                    if labelledby:
                        refined_selector = f'{tag_name}[aria-labelledby="{labelledby}"]'
                    else:
                        pass  # Fall through to regular discovery

                if 'refined_selector' in locals():
                    logger.info(f'[DISCOVERY] Tier 1 ✅ aria-label (scoped): {refined_selector}')
                    ulog.discovery(strategy="aria-label", selector=refined_selector, stable=True)
                    return {
                        "selector": refined_selector,
                        "score": 0.98,
                        "meta": {"strategy": "aria_label_scoped", "stable": True, "tier": 1}
                    }
        except Exception as e:
            logger.debug(f"[DISCOVERY] Tier 1 scoped discovery failed: {e}")

    # Fall back to regular exact/fuzzy matching
    try:
        # Try exact aria-label match
        selector = f'[aria-label="{name}"]'
        count = await browser.locator_count(selector)

        if count == 1:
            el_handle = await browser.page.locator(selector).first.element_handle()
            if el_handle and await _check_visibility(browser, selector, el_handle):
                if not await _is_fillable_element(browser, selector, el_handle, action):
                    return None

                # Refine selector with tag name for better specificity
                tag_name = await el_handle.evaluate("el => el.tagName.toLowerCase()")
                refined_selector = f'{tag_name}[aria-label="{name}"]'

                logger.info(f'[DISCOVERY] Tier 1 ✅ aria-label: {refined_selector}')
                ulog.discovery(strategy="aria-label", selector=refined_selector, stable=True)
                return {
                    "selector": refined_selector,
                    "score": 0.98,
                    "meta": {"strategy": "aria_label", "stable": True, "tier": 1}
                }

        # Try fuzzy aria-label match
        pattern = create_fuzzy_pattern(name)
        all_elements = await browser.page.locator('[aria-label]').all()

        for el in all_elements:
            aria_val = await el.get_attribute("aria-label")
            if aria_val and pattern.search(aria_val):
                # Semantic filtering: Reject UI control aria-labels for form fill actions
                # These are table/UI controls, not actual form fields
                UI_CONTROL_KEYWORDS = ['width', 'height', 'resize', 'column', 'row', 'sort', 'filter', 'toggle', 'expand', 'collapse']
                if action == "fill" and any(keyword in aria_val.lower() for keyword in UI_CONTROL_KEYWORDS):
                    logger.debug(f"[DISCOVERY] Tier 1 fuzzy: Rejecting UI control aria-label={aria_val}")
                    continue

                if await _check_visibility(browser, "", el):
                    # Validate element is appropriate for the action (skip sliders, color pickers, etc.)
                    if not await _is_fillable_element(browser, "", el, action):
                        logger.debug(f"[DISCOVERY] Tier 1 fuzzy: Skipping non-fillable aria-label={aria_val}")
                        continue

                    tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                    refined_selector = f'{tag_name}[aria-label="{aria_val}"]'

                    logger.info(f'[DISCOVERY] Tier 1 ✅ aria-label (fuzzy): {refined_selector}')
                    ulog.discovery(strategy="aria-label-fuzzy", selector=refined_selector, stable=True)
                    return {
                        "selector": refined_selector,
                        "score": 0.96,
                        "meta": {"strategy": "aria_label_fuzzy", "stable": True, "tier": 1}
                    }

    except Exception as e:
        logger.debug(f"[DISCOVERY] Tier 1 aria-label failed: {e}")

    return None


async def _try_aria_placeholder(browser, intent) -> Optional[Dict[str, Any]]:
    """
    Tier 2: aria-placeholder (STABLE)

    Semantic placeholder attribute, stable across frameworks.
    """
    name = intent.get("element") or intent.get("placeholder") or intent.get("intent")
    if not name:
        return None

    try:
        # Try exact aria-placeholder match
        selector = f'[aria-placeholder="{name}"]'
        count = await browser.locator_count(selector)

        if count == 1:
            el_handle = await browser.page.locator(selector).first.element_handle()
            if el_handle and await _check_visibility(browser, selector, el_handle):
                tag_name = await el_handle.evaluate("el => el.tagName.toLowerCase()")
                refined_selector = f'{tag_name}[aria-placeholder="{name}"]'

                logger.info(f'[DISCOVERY] Tier 2 ✅ aria-placeholder: {refined_selector}')
                return {
                    "selector": refined_selector,
                    "score": 0.96,
                    "meta": {"strategy": "aria_placeholder", "stable": True, "tier": 2}
                }

        # Try fuzzy match
        pattern = create_fuzzy_pattern(name)
        all_elements = await browser.page.locator('[aria-placeholder]').all()

        for el in all_elements:
            aria_val = await el.get_attribute("aria-placeholder")
            if aria_val and pattern.search(aria_val):
                if await _check_visibility(browser, "", el):
                    tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                    refined_selector = f'{tag_name}[aria-placeholder="{aria_val}"]'

                    logger.info(f'[DISCOVERY] Tier 2 ✅ aria-placeholder (fuzzy): {refined_selector}')
                    return {
                        "selector": refined_selector,
                        "score": 0.94,
                        "meta": {"strategy": "aria_placeholder_fuzzy", "stable": True, "tier": 2}
                    }

    except Exception as e:
        logger.debug(f"[DISCOVERY] Tier 2 aria-placeholder failed: {e}")

    return None


async def _try_name_attr(browser, intent) -> Optional[Dict[str, Any]]:
    """
    Tier 3: name attribute (STABLE)

    Form field name attribute - stable, semantic, universal.
    """
    name = intent.get("element") or intent.get("label") or intent.get("intent")
    if not name:
        return None

    normalized_name = normalize_text(name)

    try:
        # Try exact name attribute match
        selector = f'[name="{name}"]'
        count = await browser.locator_count(selector)

        if count == 1:
            el_handle = await browser.page.locator(selector).first.element_handle()
            if el_handle and await _check_visibility(browser, selector, el_handle):
                tag_name = await el_handle.evaluate("el => el.tagName.toLowerCase()")
                refined_selector = f'{tag_name}[name="{name}"]'

                logger.info(f'[DISCOVERY] Tier 3 ✅ name: {refined_selector}')
                return {
                    "selector": refined_selector,
                    "score": 0.94,
                    "meta": {"strategy": "name_attr", "stable": True, "tier": 3}
                }

        # Try fuzzy name matching (handle Name vs name vs NAME)
        pattern = create_fuzzy_pattern(name)
        all_elements = await browser.page.locator('[name]').all()

        for el in all_elements:
            name_val = await el.get_attribute("name")
            if name_val and pattern.search(name_val):
                if await _check_visibility(browser, "", el):
                    tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                    refined_selector = f'{tag_name}[name="{name_val}"]'

                    logger.info(f'[DISCOVERY] Tier 3 ✅ name (fuzzy): {refined_selector}')
                    return {
                        "selector": refined_selector,
                        "score": 0.92,
                        "meta": {"strategy": "name_attr_fuzzy", "stable": True, "tier": 3}
                    }

    except Exception as e:
        logger.debug(f"[DISCOVERY] Tier 3 name failed: {e}")

    return None


async def _try_placeholder_attr(browser, intent) -> Optional[Dict[str, Any]]:
    """
    Tier 4: placeholder attribute (STABLE)

    HTML placeholder attribute - stable, user-visible hint.
    """
    name = intent.get("element") or intent.get("placeholder") or intent.get("intent")
    if not name:
        return None

    try:
        # Try exact placeholder match
        selector = f'[placeholder="{name}"]'
        count = await browser.locator_count(selector)

        if count == 1:
            el_handle = await browser.page.locator(selector).first.element_handle()
            if el_handle and await _check_visibility(browser, selector, el_handle):
                placeholder_val = await el_handle.get_attribute("placeholder")
                refined_selector = f'input[placeholder="{placeholder_val}"]'

                logger.info(f'[DISCOVERY] Tier 4 ✅ placeholder: {refined_selector}')
                return {
                    "selector": refined_selector,
                    "score": 0.90,
                    "meta": {"strategy": "placeholder_attr", "stable": True, "tier": 4}
                }

        # Try fuzzy placeholder match
        pattern = create_fuzzy_pattern(name)
        all_elements = await browser.page.locator('[placeholder]').all()

        for el in all_elements:
            placeholder_val = await el.get_attribute("placeholder")
            if placeholder_val and pattern.search(placeholder_val):
                if await _check_visibility(browser, "", el):
                    refined_selector = f'input[placeholder="{placeholder_val}"]'

                    logger.info(f'[DISCOVERY] Tier 4 ✅ placeholder (fuzzy): {refined_selector}')
                    return {
                        "selector": refined_selector,
                        "score": 0.88,
                        "meta": {"strategy": "placeholder_attr_fuzzy", "stable": True, "tier": 4}
                    }

    except Exception as e:
        logger.debug(f"[DISCOVERY] Tier 4 placeholder failed: {e}")

    return None


async def _try_label_for(browser, intent) -> Optional[Dict[str, Any]]:
    """
    Tier 5: <label for> proximity (STABLE)

    HTML label element pointing to input via for attribute.
    """
    name = intent.get("element") or intent.get("label") or intent.get("intent")
    if not name:
        return None

    try:
        # Find label elements with matching text
        pattern = create_fuzzy_pattern(name)
        all_labels = await browser.page.locator('label').all()

        for label_el in all_labels:
            label_text = await label_el.inner_text()
            if label_text and pattern.search(label_text):
                # Check for 'for' attribute
                label_for = await label_el.get_attribute("for")
                if label_for:
                    # Find input with matching id
                    input_selector = f'#{label_for}'
                    input_el = await browser.page.locator(input_selector).element_handle()

                    if input_el and await _check_visibility(browser, input_selector, input_el):
                        tag_name = await input_el.evaluate("el => el.tagName.toLowerCase()")
                        refined_selector = f'{tag_name}#{label_for}'

                        logger.info(f'[DISCOVERY] Tier 5 ✅ label[for]: {refined_selector}')
                        return {
                            "selector": refined_selector,
                            "score": 0.86,
                            "meta": {"strategy": "label_for", "stable": True, "tier": 5}
                        }

    except Exception as e:
        logger.debug(f"[DISCOVERY] Tier 5 label[for] failed: {e}")

    return None


async def _try_data_attr(browser, intent) -> Optional[Dict[str, Any]]:
    """
    Tier 7: data-* attribute (STABLE)

    data-testid, data-test, data-qa, data-cy, data-automation - stable test hooks.
    """
    name = intent.get("element") or intent.get("intent")
    if not name:
        return None

    normalized_name = normalize_text(name)

    # Common data attribute patterns
    data_attrs = [
        "data-testid",
        "data-test",
        "data-qa",
        "data-cy",
        "data-automation",
        "data-test-id",
    ]

    try:
        pattern = create_fuzzy_pattern(name)

        for attr in data_attrs:
            all_elements = await browser.page.locator(f'[{attr}]').all()

            for el in all_elements:
                attr_val = await el.get_attribute(attr)
                if attr_val and pattern.search(attr_val):
                    if await _check_visibility(browser, "", el):
                        tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                        refined_selector = f'{tag_name}[{attr}="{attr_val}"]'

                        logger.info(f'[DISCOVERY] Tier 7 ✅ data-attr: {refined_selector}')
                        return {
                            "selector": refined_selector,
                            "score": 0.80,
                            "meta": {"strategy": "data_attr", "stable": True, "tier": 7}
                        }

    except Exception as e:
        logger.debug(f"[DISCOVERY] Tier 7 data-attr failed: {e}")

    return None


async def _try_id_class(browser, intent) -> Optional[Dict[str, Any]]:
    """
    Tier 8: id / class (VOLATILE - Last Resort)

    Framework-generated IDs and classes - volatile, single-use only.
    """
    name = intent.get("element") or intent.get("intent")
    if not name:
        return None

    try:
        pattern = create_fuzzy_pattern(name)

        # Try ID match (last resort - often volatile)
        all_elements_with_id = await browser.page.locator('[id]').all()

        for el in all_elements_with_id:
            el_id = await el.get_attribute("id")
            if el_id and pattern.search(el_id):
                if await _check_visibility(browser, "", el):
                    refined_selector = f'#{el_id}'

                    logger.warning(f'[DISCOVERY] Tier 8 ⚠ id (VOLATILE): {refined_selector}')
                    return {
                        "selector": refined_selector,
                        "score": 0.70,
                        "meta": {"strategy": "id_class", "stable": False, "tier": 8, "volatile": True}
                    }

        # Try class match (last resort - often framework-generated)
        all_elements_with_class = await browser.page.locator('[class]').all()

        for el in all_elements_with_class:
            class_val = await el.get_attribute("class")
            if class_val and pattern.search(class_val):
                if await _check_visibility(browser, "", el):
                    # Use first class name
                    first_class = class_val.split()[0] if class_val else None
                    if first_class:
                        refined_selector = f'.{first_class}'

                        logger.warning(f'[DISCOVERY] Tier 8 ⚠ class (VOLATILE): {refined_selector}')
                        return {
                            "selector": refined_selector,
                            "score": 0.65,
                            "meta": {"strategy": "id_class", "stable": False, "tier": 8, "volatile": True}
                        }

    except Exception as e:
        logger.debug(f"[DISCOVERY] Tier 8 id/class failed: {e}")

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy Week 4-7 Strategies (Backwards Compatibility)
# ═══════════════════════════════════════════════════════════════════════════════

async def _try_label(browser, intent) -> Optional[Dict[str, Any]]:
    name = intent.get("element") or intent.get("label") or intent.get("intent")
    if not name:
        return None

    normalized_name = normalize_text(name)
    action = intent.get("action", "fill")

    # Week 4: Try aria-label first (stable selector)
    try:
        from backend.runtime.salesforce_helpers import build_input_selector_from_attrs, build_combobox_button_selector

        # Try finding element by aria-label directly
        aria_label_selector = f'[aria-label="{name}"]'
        count = await browser.locator_count(aria_label_selector)
        if count > 0:
            el_handle = await browser.page.locator(aria_label_selector).first.element_handle()
            if el_handle and await _check_visibility(browser, aria_label_selector, el_handle):
                # Check if it's an input or button
                tag_name = await el_handle.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "input":
                    stable_sel = f'input[aria-label="{name}"]'
                elif tag_name == "button":
                    stable_sel = f'button[aria-label="{name}"]'
                else:
                    stable_sel = aria_label_selector

                return {
                    "selector": stable_sel,
                    "score": 0.95,
                    "meta": {"strategy": "aria_label", "name": name, "stable": True}
                }
    except Exception as e:
        logger.debug(f"[Discovery] aria-label strategy failed: {e}")

    # Try exact match (existing logic)
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

        # Week 4: Try to build stable selector from element attributes
        try:
            from backend.runtime.salesforce_helpers import build_input_selector_from_attrs, build_combobox_button_selector

            # Extract attributes from found element
            attrs = {}
            if el:
                attrs["aria-label"] = await el.get_attribute("aria-label")
                attrs["name"] = await el.get_attribute("name")
                attrs["placeholder"] = await el.get_attribute("placeholder")

                # Try to build stable selector
                tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "input":
                    stable_sel = build_input_selector_from_attrs(attrs)
                    if stable_sel:
                        return {"selector": stable_sel, "score": 0.93, "meta": {"strategy": "label_stable", "name": name, "stable": True}}
                elif tag_name == "button":
                    stable_sel = build_combobox_button_selector(attrs)
                    if stable_sel:
                        return {"selector": stable_sel, "score": 0.93, "meta": {"strategy": "label_stable", "name": name, "stable": True}}
        except Exception as e:
            logger.debug(f"[Discovery] Stable selector build failed, using default: {e}")

        # Fallback to original ID-based selector
        return {"selector": selector, "score": 0.92, "meta": {"strategy": "label", "name": name, "normalized": normalized_name, "stable": False}}

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

        # Week 4: Try stable selector for fuzzy match too
        try:
            from backend.runtime.salesforce_helpers import build_input_selector_from_attrs

            attrs = {}
            if el:
                attrs["aria-label"] = await el.get_attribute("aria-label")
                attrs["name"] = await el.get_attribute("name")
                attrs["placeholder"] = await el.get_attribute("placeholder")

                stable_sel = build_input_selector_from_attrs(attrs)
                if stable_sel:
                    return {"selector": stable_sel, "score": 0.91, "meta": {"strategy": "label_fuzzy_stable", "name": name, "stable": True}}
        except Exception:
            pass

        return {"selector": selector, "score": 0.90, "meta": {"strategy": "label_fuzzy", "name": name, "normalized": normalized_name, "stable": False}}

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

        # Week 4: Build stable placeholder selector
        try:
            placeholder_val = await el.get_attribute("placeholder")
            if placeholder_val:
                stable_sel = f'input[placeholder="{placeholder_val}"]'
                return {"selector": stable_sel, "score": 0.89, "meta": {"strategy": "placeholder", "name": name, "stable": True}}
        except Exception:
            pass

        return {"selector": selector, "score": 0.88, "meta": {"strategy": "placeholder", "name": name, "normalized": normalized_name, "stable": False}}

    # Try fuzzy match
    fuzzy_pattern = create_fuzzy_pattern(normalized_name)
    found = await browser.find_by_placeholder(fuzzy_pattern)
    if found:
        selector, el = found
        # Check visibility - skip hidden elements
        if not await _check_visibility(browser, selector, el):
            logger.debug(f"[Discovery] Placeholder fuzzy match '{selector}' is hidden, trying next strategy")
            return None

        # Week 4: Build stable placeholder selector for fuzzy match too
        try:
            placeholder_val = await el.get_attribute("placeholder")
            if placeholder_val:
                stable_sel = f'input[placeholder="{placeholder_val}"]'
                return {"selector": stable_sel, "score": 0.87, "meta": {"strategy": "placeholder_fuzzy", "name": name, "stable": True}}
        except Exception:
            pass

        return {"selector": selector, "score": 0.86, "meta": {"strategy": "placeholder_fuzzy", "name": name, "normalized": normalized_name, "stable": False}}

    return None

async def _try_email_type(browser, intent) -> Optional[Dict[str, Any]]:
    """Week 6: Fallback for email fields that use type='email' instead of name/label"""
    name = intent.get("element") or intent.get("intent") or ""
    normalized_name = normalize_text(name)

    # Only apply to fields with "email" in the name
    if "email" not in normalized_name:
        return None

    # Try to find input[type="email"]
    try:
        selector = 'input[type="email"]'
        count = await browser.locator_count(selector)

        if count == 1:
            # Unique email field found
            logger.info(f"[Discovery] Found unique email field via type='email'")
            return {
                "selector": selector,
                "score": 0.88,
                "meta": {
                    "strategy": "type_email",
                    "name": name,
                    "stable": True  # type attribute is stable
                }
            }
        elif count > 1:
            logger.debug(f"[Discovery] Multiple email fields found (count={count}), skipping type='email' strategy")
    except Exception as e:
        logger.debug(f"[Discovery] Email type strategy failed: {e}")

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
        # Phase 4a: Don't force button for click - let keyword mapping decide
        # Check if it looks like a link/result pattern
        if any(kw in normalized_name for kw in ["video", "result", "first", "link", "article"]):
            role = "link"  # Likely a clickable result, not a button
        else:
            role = "button"
    elif action == "fill":
        # Phase 4a: For fill actions, try searchbox role first
        role = "searchbox"

    # Keyword mapping (check normalized name for hints)
    for key, r in ROLE_HINTS.items():
        if key in normalized_name:
            role = r
            break

    # Final fallback: try common roles
    # Phase 4a: Include searchbox for fill actions, article for click
    if action == "fill":
        candidates = [role] if role else ["searchbox", "textbox", "combobox"]
    else:
        candidates = [role] if role else ["button", "link", "article", "tab"]

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

            # Phase 4a-C: Non-Unique Selector Handling (v3.1s Stealth 2.0)
            # Check if multiple elements match (for ALL roles, not just common buttons)
            locator = browser.page.get_by_role(r, name=exact_pattern)
            count = await locator.count()

            if count > 1:
                logger.info(f"[Discovery] Phase 4a-C: Non-unique {r} match ({count} elements), applying fallbacks")

                # Fallback 1: Try text-based CSS selector (YouTube filter chips case)
                try:
                    text_selector = f'{r}:has-text("{name}")'
                    text_locator = browser.page.locator(text_selector)
                    text_count = await text_locator.count()

                    if text_count == 1:
                        logger.info(f"[Discovery] Phase 4a-C: Text-based selector is unique: {text_selector}")
                        text_el = await text_locator.first.element_handle()
                        if text_el and await _check_visibility(browser, text_selector, text_el):
                            return {
                                "selector": text_selector,
                                "score": 0.93,
                                "meta": {"strategy": "role_name_text_fallback", "role": r, "name": name, "count": count}
                            }
                except Exception as e:
                    logger.debug(f"[Discovery] Phase 4a-C: Text fallback failed: {e}")

                # Fallback 2: Disambiguate common action buttons (New, Save, Edit, Delete)
                if r == "button" and normalized_name in ["new", "save", "edit", "delete", "cancel", "submit"]:
                    logger.info(f"[Discovery] 🔍 Multiple '{normalized_name}' buttons found ({count}), disambiguating...")

                    # Strategy: Find button in main action toolbar (not in tabs/headers)
                    # Filter out buttons that are part of tab strips or other compound elements
                    for i in range(count):
                        candidate_el = await locator.nth(i).element_handle()
                        if candidate_el:
                            # Check if button is inside a tab element (avoid tab headers with "New" in name)
                            parent_role = await candidate_el.evaluate("el => el.closest('[role=\"tab\"]') ? 'tab' : null")
                            if parent_role == "tab":
                                logger.debug(f"[Discovery] Skipping button #{i} - inside tab element")
                                continue

                            # Check if button is in a close/dismiss context (tab close buttons)
                            aria_label = await candidate_el.get_attribute("aria-label")
                            title = await candidate_el.get_attribute("title")
                            if (aria_label and ("close" in aria_label.lower() or "remove" in aria_label.lower())) or \
                               (title and ("close" in title.lower() or "remove" in title.lower())):
                                logger.debug(f"[Discovery] Skipping button #{i} - close/remove button")
                                continue

                            # This is likely the primary action button
                            logger.info(f"[Discovery] ✅ Found primary '{normalized_name}' button at position {i}")
                            # Get stable selector for this specific button
                            button_id = await candidate_el.get_attribute("id")
                            if button_id:
                                selector = f"#{button_id}"
                            else:
                                # Phase 4a: Use proper Playwright regex syntax
                                selector = f"role=button[name=/{normalized_name}/i] >> nth={i}"

                            return {
                                "selector": selector,
                                "score": 0.95,
                                "meta": {"strategy": "role_name_disambiguated", "role": r, "name": name, "normalized": normalized_name, "position": i}
                            }

                # Fallback 3: Last resort - use nth with Playwright role API (more stable than CSS nth)
                logger.warning(f"[Discovery] Phase 4a-C: Using nth(0) fallback for non-unique {r} (may be brittle)")
                first_el = await locator.first.element_handle()
                if first_el:
                    el_id = await first_el.get_attribute("id")
                    if el_id:
                        selector = f"#{el_id}"
                    else:
                        # Prefer role locator with nth over CSS nth (more stable)
                        selector = f'role={r}[name="{name}" i] >> nth=0'

                    return {
                        "selector": selector,
                        "score": 0.84,  # Slightly higher confidence for role nth
                        "meta": {"strategy": "role_name_nth_locator", "role": r, "name": name, "count": count, "warning": "non_unique"}
                    }

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

async def _try_youtube_video(browser, intent) -> Optional[Dict[str, Any]]:
    """Phase 4a: YouTube-specific video result detection"""
    name = (intent.get("element") or intent.get("intent") or "").strip().lower()

    # Only apply to video/result patterns
    if not any(kw in name for kw in ["video", "result", "first"]):
        return None

    try:
        # YouTube video results have id="video-title" links
        video_links = browser.page.locator('a#video-title')
        count = await video_links.count()

        if count > 0:
            logger.info(f"[Discovery] Phase 4a: Found {count} YouTube video results")
            # First video result
            first_video = video_links.first
            if await first_video.is_visible():
                return {
                    "selector": "a#video-title >> nth=0",
                    "score": 0.94,
                    "meta": {"strategy": "youtube_video", "name": name, "count": count}
                }
    except Exception as e:
        logger.debug(f"[Discovery] YouTube video strategy failed: {e}")

    return None

async def _try_reddit_search(browser, intent) -> Optional[Dict[str, Any]]:
    """Phase 4a: Reddit-specific search box detection with activation"""
    name = (intent.get("element") or intent.get("intent") or "").strip().lower()
    action = intent.get("action", "").lower()

    # Only apply to search patterns on fill actions
    if action != "fill" or "search" not in name:
        return None

    try:
        # First, try to find existing visible search input
        reddit_selectors = [
            'input[name="q"]',  # Old Reddit
            'input[type="search"]',  # New Reddit
            'input[placeholder*="Search" i]',  # Generic search
            'input[aria-label*="Search" i]',  # Accessible search
        ]

        for sel in reddit_selectors:
            locator = browser.page.locator(sel)
            count = await locator.count()
            if count > 0:
                first = locator.first
                try:
                    if await first.is_visible() and await first.is_editable():
                        logger.info(f"[Discovery] Phase 4a: Found Reddit search via {sel}")
                        return {
                            "selector": sel,
                            "score": 0.93,
                            "meta": {"strategy": "reddit_search", "name": name}
                        }
                except Exception:
                    continue

        # If not found, try activating search (Reddit may have hidden/collapsed search)
        # Try clicking search icon/button first
        search_activators = [
            'button[aria-label*="Search" i]',
            'a[href*="search"]',
            '[data-testid="search-icon"]',
        ]

        for activator_sel in search_activators:
            try:
                activator = browser.page.locator(activator_sel).first
                if await activator.is_visible():
                    await activator.click(timeout=2000)
                    await browser.page.wait_for_timeout(500)

                    # Re-try finding search input after activation
                    for sel in reddit_selectors:
                        locator = browser.page.locator(sel)
                        if await locator.count() > 0:
                            first = locator.first
                            if await first.is_visible() and await first.is_editable():
                                logger.info(f"[Discovery] Phase 4a: Found Reddit search after activation via {sel}")
                                return {
                                    "selector": sel,
                                    "score": 0.92,
                                    "meta": {"strategy": "reddit_search_activated", "name": name, "activator": activator_sel}
                                }
                    break
            except Exception:
                continue

    except Exception as e:
        logger.debug(f"[Discovery] Reddit search strategy failed: {e}")

    return None

async def _try_booking_destination(browser, intent) -> Optional[Dict[str, Any]]:
    """Phase 4a: Booking.com destination/location field detection"""
    name = (intent.get("element") or intent.get("intent") or "").strip().lower()
    action = intent.get("action", "").lower()

    # Only apply to destination/location patterns on fill actions
    if action != "fill" or not any(kw in name for kw in ["destination", "where", "location", "city"]):
        return None

    try:
        # Strategy 1: Try searchbox role (Booking.com uses this)
        searchbox = browser.page.get_by_role("searchbox").first
        if await searchbox.count() > 0 and await searchbox.is_visible():
            logger.info("[Discovery] Phase 4a: Found Booking destination via searchbox role")
            return {
                "selector": "role=searchbox",
                "score": 0.95,
                "meta": {"strategy": "booking_destination_searchbox", "name": name}
            }

        # Strategy 2: Try combobox with destination text
        combobox = browser.page.get_by_role("combobox", name=re.compile(r"destination|where are you going", re.I)).first
        if await combobox.count() > 0 and await combobox.is_visible():
            logger.info("[Discovery] Phase 4a: Found Booking destination via combobox role")
            return {
                "selector": 'role=combobox[name=/destination|where are you going/i]',
                "score": 0.94,
                "meta": {"strategy": "booking_destination_combobox", "name": name}
            }

        # Strategy 3: Canonical Booking.com selector
        canonical = browser.page.locator('input[name="ss"]').first
        if await canonical.count() > 0 and await canonical.is_visible():
            logger.info("[Discovery] Phase 4a: Found Booking destination via canonical name=ss")
            return {
                "selector": 'input[name="ss"]',
                "score": 0.96,
                "meta": {"strategy": "booking_destination_canonical", "name": name}
            }

        # Strategy 4: Placeholder-based
        placeholder = browser.page.get_by_placeholder(re.compile(r"where are you going|destination", re.I)).first
        if await placeholder.count() > 0 and await placeholder.is_visible():
            logger.info("[Discovery] Phase 4a: Found Booking destination via placeholder")
            return {
                "selector": 'input[placeholder*="Where are you going"]',
                "score": 0.93,
                "meta": {"strategy": "booking_destination_placeholder", "name": name}
            }

    except Exception as e:
        logger.debug(f"[Discovery] Booking destination strategy failed: {e}")

    return None

async def _try_booking_autocomplete(browser, intent) -> Optional[Dict[str, Any]]:
    """Phase 4a: Universal autocomplete - returns first listbox option using ARIA roles"""
    name = (intent.get("element") or intent.get("intent") or "").strip().lower()
    action = intent.get("action", "").lower()

    # Only apply to autocomplete/suggestion patterns on click actions
    if action != "click" or not any(kw in name for kw in ["autocomplete", "suggestion", "first", "option"]):
        return None

    try:
        # Look for ARIA listbox with options (universal, works for any autocomplete)
        listbox = browser.page.get_by_role("listbox").first
        if await listbox.count() > 0:
            # Wait briefly for options to render
            await browser.page.wait_for_timeout(200)

            # Check if listbox has visible options
            options = listbox.get_by_role("option")
            option_count = await options.count()

            if option_count > 0:
                # Check if first option is visible
                first_option = options.first
                try:
                    await first_option.wait_for(state="visible", timeout=2000)
                    logger.info(f"[Discovery] Phase 4a: Found autocomplete with {option_count} options, returning first")
                    # Return selector for first option in the listbox
                    # Use Playwright's role selector - completely generic, no hardcoding
                    return {
                        "selector": "role=listbox >> role=option >> nth=0",
                        "score": 0.96,
                        "meta": {
                            "strategy": "autocomplete_first_option_aria",
                            "name": name,
                            "option_count": option_count
                        }
                    }
                except Exception:
                    pass  # First option not visible yet

    except Exception as e:
        logger.debug(f"[Discovery] Autocomplete option strategy failed: {e}")

    return None

async def _try_fallback_css(browser, intent) -> Optional[Dict[str, Any]]:
    return None

# Week 8 EDR: Universal Discovery Strategy Function Mapping
STRATEGY_FUNCS = {
    # Universal 8-Tier Hierarchy
    "aria_label": _try_aria_label,
    "aria_placeholder": _try_aria_placeholder,
    "name_attr": _try_name_attr,
    "placeholder_attr": _try_placeholder_attr,
    "label_for": _try_label_for,
    "role_name": _try_role_name,
    "data_attr": _try_data_attr,
    "id_class": _try_id_class,
    # Legacy strategies (backwards compatibility)
    "label": _try_label,
    "placeholder": _try_placeholder,
    "email_type": _try_email_type,
    # Phase 4a: Site-specific strategies
    "youtube_video": _try_youtube_video,
    "reddit_search": _try_reddit_search,
    "booking_destination": _try_booking_destination,
    "booking_autocomplete": _try_booking_autocomplete,
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

    # CRITICAL: Wait for page to stabilize before discovery (Salesforce SPAs load async)
    # This prevents premature discovery when elements haven't rendered yet
    try:
        await browser.page.wait_for_load_state("domcontentloaded", timeout=3000)
        await browser.page.wait_for_timeout(500)  # Reduced settle time for non-SF sites
    except Exception:
        pass  # Non-critical - continue with discovery

    # Week 5: Lightning list page readiness (prevents "New" button timeout)
    # Phase 4a: Only call Lightning readiness on Lightning pages (avoid non-SF overhead)
    try:
        if "lightning.force.com" in (browser.page.url or "").lower():
            await ensure_lightning_ready_list(browser.page)
    except Exception:
        pass  # Non-critical - continue with discovery

    # ═══════════════════════════════════════════════════════════════════════════════
    # Week 8 Phase B: Scope-First Discovery (Generic Container Resolution)
    # ═══════════════════════════════════════════════════════════════════════════════
    scope_container = None
    scope_enabled = os.getenv("PACTS_SCOPE_FEATURE", "true").lower() == "true"

    if scope_enabled and within:
        try:
            from backend.runtime.scope_helpers import resolve_container, wait_scope_ready

            logger.info(f"[SCOPE] Phase B: Resolving container for within='{within}'")

            # Resolve the container (dialog → tabpanel → form → main → page)
            scope_container = await resolve_container(browser.page, within if within != "-" else None)

            # Wait for scope to be ready
            await wait_scope_ready(scope_container)

            logger.info(f"[SCOPE] Phase B: Container resolved and ready")

        except Exception as e:
            logger.warning(f"[SCOPE] Phase B: Container resolution failed: {e}, using page scope")
            scope_container = browser.page

    # PRIORITY 0: Dialog-scoped discovery for Salesforce App Launcher (legacy)
    # TODO: Migrate this to use generic scope_container above
    if within and not scope_container:
        logger.info(f"[SCOPE] ⭐ WITHIN HINT DETECTED: target='{target}' within='{within}'")

        try:
            # Salesforce App Launcher: Use dialog-scoped locators
            if "app launcher" in within.lower():
                logger.info(f"[Discovery] 🔍 Searching for App Launcher dialog...")
                # Find the App Launcher dialog
                panel = browser.page.get_by_role("dialog", name=re.compile("app.?launcher", re.I))
                panel_count = await panel.count()

                logger.info(f"[SCOPE] 📊 App Launcher dialog count: {panel_count}")
                if panel_count > 0:
                    logger.info(f"[SCOPE] ✅ FOUND container: App Launcher (role=dialog, count={panel_count})")

                    # Try robust launcher search first (works across all orgs)
                    target_lower = target.lower()
                    if target_lower in ["accounts", "contacts", "leads", "opportunities", "cases"]:
                        # Use search box in launcher
                        search = panel.get_by_role("combobox", name=re.compile("search", re.I)).first
                        search_count = await search.count()

                        logger.info(f"[Discovery] 🔎 Launcher search box count: {search_count}")
                        if search_count > 0:
                            logger.info(f"[Discovery] ✅ Using LAUNCHER_SEARCH for '{target}'")
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
                    # Try exact match first
                    logger.info(f"[Discovery] 🔘 Trying exact button match for '{target}'...")
                    scoped_button = panel.get_by_role("button", name=re.compile(f"^{re.escape(target)}$", re.I))
                    button_count = await scoped_button.count()

                    logger.info(f"[DISCOVERY] using scoped locator (container.locator): panel.get_by_role('button')")
                    logger.info(f"[GATE] scope=within(App Launcher) count={button_count} unique={button_count == 1}")
                    if button_count > 0:
                        logger.info(f"[Discovery] ✅ Found {button_count} exact button(s) for '{target}' in App Launcher")
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

                    # Try partial match button
                    logger.info(f"[Discovery] 🔘 Trying partial button match for '{target}'...")
                    scoped_button_partial = panel.get_by_role("button", name=re.compile(re.escape(target), re.I))
                    button_partial_count = await scoped_button_partial.count()

                    logger.info(f"[Discovery] 📊 Partial button count: {button_partial_count}")
                    if button_partial_count > 0:
                        logger.info(f"[Discovery] ✅ Found {button_partial_count} partial button(s) for '{target}' in App Launcher")
                        return {
                            "selector": f'role=dialog[name*="app launcher" i] >> role=button[name*="{target}" i]',
                            "score": 0.95,
                            "meta": {
                                "strategy": "dialog_scoped_button_partial",
                                "region": within,
                                "count": button_partial_count
                            }
                        }

                    # Try link (some orgs use links instead of buttons)
                    logger.info(f"[Discovery] 🔗 Trying link match for '{target}'...")
                    scoped_link = panel.get_by_role("link", name=re.compile(f"^{re.escape(target)}$", re.I))
                    link_count = await scoped_link.count()

                    logger.info(f"[Discovery] 📊 Link count: {link_count}")
                    if link_count > 0:
                        logger.info(f"[Discovery] ✅ Found {link_count} link(s) for '{target}' in App Launcher")
                        return {
                            "selector": f'role=dialog[name*="app launcher" i] >> role=link[name="{target}" i]',
                            "score": 0.97,
                            "meta": {
                                "strategy": "dialog_scoped_link",
                                "region": within,
                                "count": link_count
                            }
                        }

                    logger.warning(f"[SCOPE] ⚠️ No buttons or links found for '{target}' in App Launcher dialog!")
                else:
                    logger.warning(f"[SCOPE] ❌ scope-not-found: App Launcher dialog (panel_count={panel_count})")

        except Exception as e:
            logger.warning(f"[Discovery] Dialog-scoped discovery failed: {e}, falling back...")

    # PRIORITY 1: MCP Discovery-Only Mode (Phase A)
    # MCP enriches discovery, all actions executed locally
    # Check MCP_ACTIONS_ENABLED flag - must be false for Phase A
    mcp_actions_enabled = os.getenv("MCP_ACTIONS_ENABLED", "false").lower() == "true"

    # Phase A: MCP actions DISABLED (discovery-only)
    if USE_MCP and not mcp_actions_enabled:
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
    for name in STRATEGIES[:4]:  # label, placeholder, email_type, role_name
        cand = await STRATEGY_FUNCS[name](browser, intent)
        if cand:
            return cand

    # Week 7: Lightning component resolver (Salesforce-specific)
    # Try this after standard strategies but before generic heuristics
    try:
        current_url = browser.page.url if browser and hasattr(browser, 'page') and browser.page else ""
        if "lightning.force.com" in current_url:
            from backend.runtime.salesforce_helpers import resolve_lightning_field
            lightning_result = await resolve_lightning_field(browser.page, target)
            if lightning_result:
                return lightning_result
    except Exception as e:
        logger.debug(f"[DISCOVERY] Lightning resolver check failed: {e}")

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

        # Week 6: Try email type strategy
        result = await _try_email_type(browser, intent)
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

    # All strategies exhausted - add debugging to see what's available
    print(f"[Discovery] ❌ All strategies exhausted for: '{element_name}'")
    try:
        # Wait a moment for page to fully load
        await browser.page.wait_for_timeout(2000)

        # List all buttons on the page for debugging
        all_buttons = browser.page.get_by_role("button")
        button_count = await all_buttons.count()
        print(f"[Discovery] 🔍 DEBUG: Found {button_count} total buttons on page")

        # Show first 15 buttons with their accessible names
        for i in range(min(15, button_count)):
            try:
                btn = all_buttons.nth(i)
                btn_name = await btn.get_attribute("aria-label") or await btn.inner_text() or "(no text)"
                btn_visible = await btn.is_visible()
                print(f"[Discovery] 🔍   Button {i}: '{btn_name[:60]}' (visible={btn_visible})")
            except Exception:
                pass
    except Exception as debug_error:
        print(f"[Discovery] Failed to debug buttons: {debug_error}")

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
