"""
Execution Patterns Registry

Codifies reusable interaction patterns for modern web applications.
These patterns handle common UX paradigms that break traditional element-selector models.
"""

from typing import Dict, List, Any
import re


class ExecutionPatterns:
    """
    Registry of proven execution patterns for handling modern web interactions.

    Each pattern encapsulates a specific UX paradigm:
    - Autocomplete: Sites that show suggestions after typing (Wikipedia, Google)
    - Activator: Buttons/triggers that reveal actual inputs (GitHub, Slack)
    - SPA Navigation: Single-page apps where DOM updates race with nav (React, Vue apps)
    """

    # Pattern: Autocomplete Bypass
    # When pressing Enter might be intercepted by autocomplete dropdown,
    # prefer clicking submit buttons instead
    AUTOCOMPLETE = {
        "description": "Bypass autocomplete dropdowns by clicking submit instead of pressing Enter",
        "triggers": {
            "roles": ["listbox", "combobox"],
            "classes": ["autocomplete", "suggestions", "dropdown", "typeahead"],
            "selectors": [
                '[role="listbox"]',
                '.suggestions-dropdown',
                '[class*="autocomplete"]',
                '[class*="search-suggestions"]'
            ]
        },
        "submit_hints": [
            "#searchButton",           # Wikipedia-specific
            "button[type='submit']",   # Standard submit
            "input[type='submit']",    # Old-school submit
            "button:has-text('Search')",  # Text-based
            "button:has-text('Go')"
        ],
        "fallback_strategy": "keyboard_enter",  # Press Enter via keyboard API if all else fails
        "timeout_ms": 3000
    }

    # Pattern: Activator-First
    # Elements that look like inputs but are actually buttons that open modals/overlays
    # with the real input inside
    ACTIVATOR = {
        "description": "Click activator buttons to reveal actual input fields",
        "detection": {
            "tag_names": ["button"],
            "types": ["button"],
            "roles": ["button", "combobox", "searchbox"],
            "selector_keywords": ["button"]  # If selector contains "button"
        },
        "post_click_wait_ms": 500,  # Wait for modal/overlay to appear
        "input_discovery": [
            "input[type='text']:visible",
            "input[type='search']:visible",
            "input:not([type]):visible",
            "textarea:visible"
        ],
        "timeout_ms": 3000
    }

    # Pattern: SPA Navigation Race
    # Single-page apps where DOM updates can happen before/instead of URL navigation
    # Success = navigation OR success DOM token appears
    SPA_NAV = {
        "description": "Race between URL navigation and DOM success indicators",
        "actions": ["press", "click"],  # Only for actions that trigger navigation
        "success_tokens": {
            "wikipedia": ["#firstHeading", "#mw-content-text"],
            "github": ["[data-search-results]", ".search-results"],
            "generic": ["main", "[role='main']", "#content", ".content"]
        },
        "timeout_ms": 4000,
        "settle_time_ms": 200  # Extra time for animations/JS after token appears
    }

    @classmethod
    def detect_autocomplete(cls, page) -> bool:
        """
        Detect if autocomplete dropdown is currently visible on the page.

        Args:
            page: Playwright page object

        Returns:
            bool: True if autocomplete is visible
        """
        # Check common autocomplete selectors
        for selector in cls.AUTOCOMPLETE["triggers"]["selectors"]:
            try:
                element = page.locator(selector).first
                if element and element.is_visible():
                    return True
            except Exception:
                continue
        return False

    @classmethod
    def is_activator(cls, tag_name: str, element_type: str, element_role: str, selector: str) -> bool:
        """
        Detect if element is an activator (button/trigger) rather than actual input.

        Args:
            tag_name: HTML tag name (e.g., "button", "input")
            element_type: Element type attribute
            element_role: ARIA role attribute
            selector: CSS selector used to find element

        Returns:
            bool: True if element is an activator
        """
        detection = cls.ACTIVATOR["detection"]

        # Check tag name
        if tag_name in detection["tag_names"]:
            return True

        # Check type attribute
        if element_type in detection["types"]:
            return True

        # Check ARIA role
        if element_role in detection["roles"]:
            return True

        # Check if selector contains activator keywords
        selector_lower = selector.lower()
        if any(keyword in selector_lower for keyword in detection["selector_keywords"]):
            return True

        return False

    @classmethod
    def get_submit_selectors(cls) -> List[str]:
        """Get prioritized list of submit button selectors for autocomplete bypass."""
        return cls.AUTOCOMPLETE["submit_hints"]

    @classmethod
    def get_activator_input_selectors(cls) -> List[str]:
        """Get selectors for finding actual input after clicking activator."""
        return cls.ACTIVATOR["input_discovery"]

    @classmethod
    def get_spa_success_tokens(cls, site_hint: str = None) -> List[str]:
        """
        Get DOM success tokens for SPA navigation detection.

        Args:
            site_hint: Optional hint about the site (e.g., "wikipedia", "github")

        Returns:
            List of CSS selectors to check for navigation success
        """
        tokens = cls.SPA_NAV["success_tokens"]

        if site_hint and site_hint.lower() in tokens:
            return tokens[site_hint.lower()]

        # Return generic tokens
        return tokens["generic"]


# Convenience functions for executor
def detect_autocomplete(page) -> bool:
    """Check if autocomplete dropdown is visible."""
    return ExecutionPatterns.detect_autocomplete(page)


def is_activator_element(tag_name: str, element_type: str, element_role: str, selector: str) -> bool:
    """Check if element is an activator button/trigger."""
    return ExecutionPatterns.is_activator(tag_name, element_type, element_role, selector)


def get_submit_selectors() -> List[str]:
    """Get submit button selectors for autocomplete bypass."""
    return ExecutionPatterns.get_submit_selectors()


def get_input_selectors() -> List[str]:
    """Get input selectors for activator pattern."""
    return ExecutionPatterns.get_activator_input_selectors()
