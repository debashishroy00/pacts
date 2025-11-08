"""
Dialog Sentinel - POC Implementation (Week 9 Phase C)

Auto-detect and close Salesforce error dialogs during test execution.

Feature Flag: PACTS_SENTINEL_FEATURE=true
"""

import os
import re
from typing import Dict, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout


class DialogSentinel:
    """
    POC: Auto-close error dialogs to prevent test failures.

    Detects:
    - Lightning error modals (role=dialog + error keywords)
    - SLDS modals with error themes
    - Known Salesforce error patterns

    Usage:
        sentinel = DialogSentinel(page)
        result = await sentinel.check_and_close()
        if result:
            print(f"Closed dialog: {result['error_message']}")
    """

    # Error keywords to detect in dialog text
    ERROR_PATTERNS = [
        r'required',
        r'invalid',
        r'duplicate',
        r'already exists',
        r'cannot be',
        r'must be',
        r'must have',
        r'error',
        r'failed',
        r'missing',
        r'not allowed'
    ]

    def __init__(self, page: Page):
        self.page = page
        self.enabled = os.getenv("PACTS_SENTINEL_FEATURE", "false").lower() == "true"

    async def check_and_close(self) -> Optional[Dict]:
        """
        Check for error dialogs and close them.

        Returns:
            Dict with action details if dialog found and closed, None otherwise
        """
        if not self.enabled:
            return None

        # Strategy 1: ARIA dialog role
        dialog_result = await self._check_aria_dialog()
        if dialog_result:
            return dialog_result

        # Strategy 2: SLDS modal
        modal_result = await self._check_slds_modal()
        if modal_result:
            return modal_result

        # Strategy 3: Force modal (legacy)
        force_result = await self._check_force_modal()
        if force_result:
            return force_result

        return None

    async def _check_aria_dialog(self) -> Optional[Dict]:
        """Check for ARIA dialog with error content."""
        try:
            dialog = self.page.locator('role=dialog').first

            # Quick visibility check with short timeout
            if not await dialog.is_visible(timeout=100):
                return None

            # Get dialog text
            text = await dialog.inner_text()

            # Check for error keywords
            if not self._has_error_keywords(text):
                return None

            # Found error dialog - emit detection log
            error_text = text[:200].replace("\n", " ").strip()
            self._emit_log(f"[SENTINEL] action=detected type=aria_dialog error={error_text}")

            # Close the dialog
            return await self._close_dialog(dialog, "aria_dialog", error_text)

        except PlaywrightTimeout:
            return None
        except Exception as e:
            # Fail silently - sentinel should never crash the test
            return None

    async def _check_slds_modal(self) -> Optional[Dict]:
        """Check for Salesforce Lightning Design System modal with error."""
        try:
            modal = self.page.locator('.slds-modal.slds-fade-in-open').first

            if not await modal.is_visible(timeout=100):
                return None

            # Check modal header for error indicators
            header = modal.locator('.slds-modal__header')
            if await header.is_visible():
                header_text = await header.inner_text()

                if self._has_error_keywords(header_text):
                    # Get body text too
                    body = modal.locator('.slds-modal__content')
                    body_text = ""
                    if await body.is_visible():
                        body_text = await body.inner_text()

                    error_text = f"{header_text} | {body_text}"[:200].replace("\n", " ").strip()
                    self._emit_log(f"[SENTINEL] action=detected type=slds_modal error={error_text}")

                    return await self._close_dialog(modal, "slds_modal", error_text)

            return None

        except PlaywrightTimeout:
            return None
        except Exception:
            return None

    async def _check_force_modal(self) -> Optional[Dict]:
        """Check for legacy Force.com modal with error."""
        try:
            modal = self.page.locator('[data-aura-class*="forceModalDialog"]').first

            if not await modal.is_visible(timeout=100):
                return None

            text = await modal.inner_text()

            if self._has_error_keywords(text):
                error_text = text[:200].replace("\n", " ").strip()
                self._emit_log(f"[SENTINEL] action=detected type=force_modal error={error_text}")

                return await self._close_dialog(modal, "force_modal", error_text)

            return None

        except PlaywrightTimeout:
            return None
        except Exception:
            return None

    async def _close_dialog(self, dialog_locator, dialog_type: str, error_text: str) -> Dict:
        """
        Close dialog using close button or ESC fallback.

        Returns dict with action details.
        """
        # Try multiple close button selectors
        close_selectors = [
            'button[title*="Close"]',
            'button[aria-label*="Close"]',
            'button.slds-modal__close',
            '.slds-modal__header button',
            'button:has-text("Close")',
            'button:has-text("Cancel")'
        ]

        close_method = None

        for selector in close_selectors:
            try:
                btn = dialog_locator.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await btn.click()
                    close_method = f"button[{selector}]"
                    self._emit_log(f"[SENTINEL] action=close_button selector={selector}")
                    break
            except:
                continue

        # Fallback to ESC key if no button found
        if not close_method:
            await self.page.keyboard.press("Escape")
            close_method = "ESC"
            self._emit_log("[SENTINEL] action=esc_fallback")

        # Wait for dialog to disappear (short timeout)
        try:
            await self.page.wait_for_selector('role=dialog', state='hidden', timeout=3000)
        except PlaywrightTimeout:
            # Dialog might have closed but selector changed - not critical
            pass

        # Wait for DOM to settle
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=3000)
        except PlaywrightTimeout:
            pass

        return {
            "action": "dialog_closed",
            "type": dialog_type,
            "error_message": error_text,
            "close_method": close_method
        }

    def _has_error_keywords(self, text: str) -> bool:
        """Check if text contains any error keywords."""
        if not text:
            return False

        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in self.ERROR_PATTERNS)

    def _emit_log(self, message: str):
        """Emit log message (print to stdout for grep parsing)."""
        print(message)
