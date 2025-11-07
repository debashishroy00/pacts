"""
Scope Helpers (Phase B - Context & Planner Cohesion)

Generic, reusable utilities for scoping element discovery to specific
regions (dialogs, tab panels, listboxes, forms).

Purpose:
- Eliminate mis-targeting by constraining discovery to relevant containers
- Support common UX patterns: modals, dropdowns, tabs
- Enable planner to inject scopes automatically via UX rules

Key Functions:
- resolve_container(): Find the appropriate scope (dialog → tabpanel → main → page)
- within(): Create scoped locator
- wait_scope_ready(): Ensure scope is visible and interactive

Emits: [SCOPE] resolved=<type> name=<name>|-

Phase A: Basic resolve_container, exclude_resizers, prefer_form_control_with_label
Phase B: Added within, wait_scope_ready, tabpanel support, ulog emissions
"""

from playwright.async_api import Page, Locator
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def resolve_container(page: Page, name: Optional[str] = None) -> Locator:
    """
    Resolve the container/region for scoped discovery (Phase B enhanced).

    Priority (first match wins):
    1. Named dialog (if name provided)
    2. Any visible dialog
    3. Active tabpanel (for tab navigation)
    4. Salesforce Lightning record edit form
    5. Main content area
    6. Page (fallback)

    Args:
        page: Playwright page object
        name: Optional dialog/container name

    Returns:
        Locator for the container (defaults to page if nothing found)

    Emits:
        [SCOPE] resolved=<type> name=<name>|-
    """
    from backend.utils import ulog

    try:
        # 1. Named dialog (e.g., "New Opportunity", "Edit Contact")
        if name:
            dialog = page.get_by_role("dialog", name=name)
            count = await dialog.count()
            if count > 0:
                ulog.emit("SCOPE", resolved="dialog", name=name)
                logger.debug(f"[SCOPE] Using named dialog: {name}")
                return dialog.first

        # 2. First visible dialog (generic modal)
        dialog = page.get_by_role("dialog").first
        if await dialog.count() > 0:
            is_visible = await dialog.is_visible()
            if is_visible:
                ulog.emit("SCOPE", resolved="dialog", name="-")
                logger.debug("[SCOPE] Using visible dialog")
                return dialog

        # 3. Active tabpanel (Phase B addition for tab navigation)
        tabpanels = page.get_by_role("tabpanel")
        if await tabpanels.count() > 0:
            for i in range(await tabpanels.count()):
                tpanel = tabpanels.nth(i)
                if await tpanel.is_visible():
                    # Check if associated tab is selected
                    aria_labelledby = await tpanel.get_attribute("aria-labelledby")
                    if aria_labelledby:
                        tab = page.locator(f"#{aria_labelledby}")
                        if await tab.count() > 0:
                            selected = await tab.get_attribute("aria-selected")
                            if selected == "true":
                                ulog.emit("SCOPE", resolved="tabpanel", name="-")
                                logger.debug("[SCOPE] Using active tabpanel")
                                return tpanel

        # 4. Salesforce Lightning record edit form
        # These are the primary form containers in Lightning UI
        sf_form_selectors = [
            'lightning-record-edit-form',  # Standard edit form
            '[data-record-edit]',          # Record edit attribute
            '[role="main"] form',          # Main form in page
        ]

        for selector in sf_form_selectors:
            form = page.locator(selector).first
            if await form.count() > 0:
                is_visible = await form.is_visible()
                if is_visible:
                    ulog.emit("SCOPE", resolved="form", name="-")
                    logger.debug(f"[SCOPE] Using Salesforce form: {selector}")
                    return form

        # 5. Main content area (fallback)
        main = page.locator('[role="main"]').first
        if await main.count() > 0:
            ulog.emit("SCOPE", resolved="main", name="-")
            logger.debug("[SCOPE] Using main content area")
            return main

    except Exception as e:
        logger.warning(f"[SCOPE] Error resolving container: {e}")

    # 6. Ultimate fallback: entire page
    ulog.emit("SCOPE", resolved="page", name="-")
    logger.debug("[SCOPE] No specific container found, using page")
    return page


def exclude_resizers(locator: Locator) -> Locator:
    """
    Filter out resizer controls, separators, and hidden UI elements.

    Common in Salesforce data tables where columns have width adjusters
    with aria-labels like "Opportunity Name column width".

    Args:
        locator: Playwright locator to filter

    Returns:
        Filtered locator excluding UI chrome elements
    """
    return locator.filter(
        lambda el: (
            el.get_attribute("role") not in ("separator", "presentation") and
            el.get_attribute("aria-hidden") != "true" and
            "column width" not in (el.get_attribute("aria-label") or "").lower() and
            "resize" not in (el.get_attribute("aria-label") or "").lower()
        )
    )


async def prefer_form_control_with_label(label_text: str, scope: Locator) -> Optional[Locator]:
    """
    Find the actual form control associated with a label.

    Uses proper label-to-control mapping via:
    1. get_by_label() (for= association)
    2. aria-labelledby relationship
    3. Proximity-based label association

    Args:
        label_text: Label text to search for
        scope: Container to search within

    Returns:
        Locator for the associated form control, or None
    """
    try:
        # 1. Try get_by_label - Playwright's semantic matching
        # This respects <label for="id"> and aria-labelledby
        control = scope.get_by_label(label_text, exact=False)

        if await control.count() > 0:
            # Filter to actual form inputs (exclude labels themselves)
            filtered = control.locator('input, textarea, select, [role="combobox"], [role="spinbutton"], [role="textbox"]')
            if await filtered.count() > 0:
                logger.debug(f"[SCOPE] Found form control via get_by_label: {label_text}")
                return filtered.first

        # 2. Try aria-labelledby relationship
        # Find elements with aria-labelledby pointing to a label with our text
        form_controls = scope.locator('input, textarea, select, [role="combobox"], [role="spinbutton"], [role="textbox"]')
        count = await form_controls.count()

        for i in range(count):
            el = form_controls.nth(i)
            labelledby_id = await el.get_attribute("aria-labelledby")
            if labelledby_id:
                # Check if the referenced label has our text
                label_el = scope.locator(f'#{labelledby_id}')
                if await label_el.count() > 0:
                    label_content = await label_el.text_content()
                    if label_content and label_text.lower() in label_content.lower():
                        logger.debug(f"[SCOPE] Found form control via aria-labelledby: {label_text}")
                        return el

    except Exception as e:
        logger.debug(f"[SCOPE] Error in prefer_form_control_with_label: {e}")

    return None


def within(scope: Locator, selector: str) -> Locator:
    """
    Create a scoped locator (Phase B addition).

    Find selector within the given scope (container-aware discovery).

    Args:
        scope: The container Locator (dialog, tabpanel, form, etc.)
        selector: The CSS/Playwright selector to find within scope

    Returns:
        Locator: Scoped locator (scope.locator(selector))

    Example:
        dialog = await resolve_container(page, "New Opportunity")
        input_field = within(dialog, 'input[name="CloseDate"]')
        await input_field.fill("2024-12-31")
    """
    return scope.locator(selector)


async def wait_scope_ready(scope: Locator, timeout: int = 8000):
    """
    Wait for scope to be visible and ready for interaction (Phase B addition).

    Ensures the container is:
    - Visible on page
    - Not animating (stable)
    - Ready for interaction

    Args:
        scope: The container Locator
        timeout: Max wait time in milliseconds (default: 8s)

    Raises:
        TimeoutError: If scope doesn't become ready within timeout

    Usage:
        dialog = await resolve_container(page, "New Contact")
        await wait_scope_ready(dialog)
        # Now safe to discover elements within dialog
    """
    logger.debug(f"[SCOPE] Waiting for scope to be ready (timeout={timeout}ms)")
    await scope.wait_for(state="visible", timeout=timeout)

    # Small stability wait (animation complete)
    await scope.page.wait_for_timeout(300)

    logger.debug("[SCOPE] Scope is ready")
