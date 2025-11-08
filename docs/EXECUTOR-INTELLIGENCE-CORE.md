# Executor Intelligence Core - Week 9 MVP

**Status**: IMPLEMENTATION READY
**Priority**: TOP 3 TOOLS (Dialog Sentinel, Grid Reader, Duplicate Disambiguator)
**Timeline**: Week 9 (5 days)
**Last Updated**: 2025-11-07

---

## Overview

The Executor Intelligence Core implements **runtime adaptation** - giving PACTS "eyes and reflexes" to handle real-world chaos during test execution.

**Week 9 MVP**: Ship the **Top 3 Tools** that deliver 80% reliability uplift:
1. **Dialog Sentinel** - Auto-close error dialogs, resume execution
2. **Grid Reader** - Auto-heal column/view drift
3. **Duplicate Disambiguator** - Deterministic record selection (phone×3 + recency×1)

---

## Architecture Integration

### Current Executor Flow (Phase A+B)
```
Step → Readiness Gate → Five-Point Gate → Execute → Next Step
                                ↓ (failure)
                         Oracle Healer (3 attempts)
```

### New Flow with Intelligence Core (Phase C)
```
Step → Readiness Gate → Five-Point Gate → Execute → Intelligence Check → Next Step
                                ↓                           ↓
                         Oracle Healer              Dialog Sentinel
                                                    Grid Reader
                                                    Duplex (disambiguator)
```

**Key Difference**: Intelligence tools run **BETWEEN** execution and next step, acting as safety net and course-corrector.

---

## Tool 1: Dialog Sentinel ⚡ CRITICAL

### Purpose
Auto-detect and close Salesforce error dialogs, then resume execution from last safe state.

### Problem Solved
**Before**: Random Lightning error modals kill entire test run
```
Fill "Account Name" with "Acme"
Click "Save"
→ [Error dialog appears: "Phone is required"]
→ Test FAILS (can't continue)
```

**After**: Dialog Sentinel intercepts, closes, resumes
```
Fill "Account Name" with "Acme"
Click "Save"
→ [Error dialog detected]
→ [Sentinel closes dialog]
→ [Resume from last safe step]
→ Fill "Phone" with "555-0100"
→ Click "Save" again
→ SUCCESS
```

### Implementation

**File**: `backend/agents/executor_intelligence.py` (new)

```python
import re
from typing import Dict, Optional
from backend.utils.ulog import ulog

class DialogSentinel:
    """
    Auto-detect and handle error dialogs during test execution.

    Monitors for:
    - Lightning error modals (role=dialog + error keywords)
    - Toast notifications with errors
    - Known Salesforce error patterns
    """

    ERROR_PATTERNS = [
        r'required',
        r'invalid',
        r'duplicate',
        r'already exists',
        r'cannot be',
        r'must be',
        r'error',
        r'failed'
    ]

    def __init__(self, page):
        self.page = page
        self.last_safe_step = 0
        self.error_history = []

    async def check_for_dialogs(self) -> Optional[Dict]:
        """
        Check if error dialog is present and handle it.

        Returns:
            Dict with action taken, or None if no dialog found
        """
        # Check for Lightning error dialog
        error_dialog = await self._detect_error_dialog()

        if error_dialog:
            return await self._handle_dialog(error_dialog)

        # Check for toast errors (non-blocking but informative)
        toast_error = await self._detect_toast_error()

        if toast_error:
            return await self._handle_toast(toast_error)

        return None

    async def _detect_error_dialog(self) -> Optional[Dict]:
        """
        Detect Lightning error dialog using multiple strategies.

        Strategies:
        1. role=dialog with error text
        2. .slds-modal with error indicators
        3. [data-aura-class*="forceModalDialog"] with error
        """
        # Strategy 1: ARIA dialog role
        dialog = self.page.locator('role=dialog').first

        if await dialog.is_visible():
            text = await dialog.inner_text()

            # Check if text contains error keywords
            for pattern in self.ERROR_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    return {
                        "type": "aria_dialog",
                        "text": text,
                        "locator": dialog
                    }

        # Strategy 2: Salesforce modal class
        modal = self.page.locator('.slds-modal.slds-fade-in-open').first

        if await modal.is_visible():
            # Check for error header
            header = modal.locator('.slds-modal__header')
            if await header.is_visible():
                header_text = await header.inner_text()
                if any(re.search(p, header_text, re.IGNORECASE) for p in self.ERROR_PATTERNS):
                    body_text = await modal.locator('.slds-modal__content').inner_text()
                    return {
                        "type": "slds_modal",
                        "text": f"{header_text} | {body_text}",
                        "locator": modal
                    }

        # Strategy 3: Force modal (legacy)
        force_modal = self.page.locator('[data-aura-class*="forceModalDialog"]').first

        if await force_modal.is_visible():
            text = await force_modal.inner_text()
            if any(re.search(p, text, re.IGNORECASE) for p in self.ERROR_PATTERNS):
                return {
                    "type": "force_modal",
                    "text": text,
                    "locator": force_modal
                }

        return None

    async def _detect_toast_error(self) -> Optional[Dict]:
        """
        Detect error toast notifications.

        Toast patterns:
        - .slds-notify--toast with error theme
        - role=alert with error text
        """
        # Check for error-themed toast
        error_toast = self.page.locator('.slds-notify--toast.slds-theme--error, .slds-notify--toast.slds-theme--warning').first

        if await error_toast.is_visible():
            text = await error_toast.inner_text()
            return {
                "type": "toast_error",
                "text": text,
                "severity": "error" if "slds-theme--error" in await error_toast.get_attribute("class") else "warning"
            }

        # Check for generic alert
        alert = self.page.locator('role=alert').first

        if await alert.is_visible():
            text = await alert.inner_text()
            if any(re.search(p, text, re.IGNORECASE) for p in self.ERROR_PATTERNS):
                return {
                    "type": "alert",
                    "text": text,
                    "severity": "unknown"
                }

        return None

    async def _handle_dialog(self, dialog_info: Dict) -> Dict:
        """
        Close error dialog and prepare for recovery.

        Steps:
        1. Log error details
        2. Extract error message
        3. Find and click close button
        4. Wait for dialog to disappear
        5. Wait for DOM idle
        6. Return recovery plan
        """
        error_text = dialog_info["text"][:200]  # Truncate for logging

        # Emit telemetry
        ulog.emit("[SENTINEL] action=detected type={type} error={error}".format(
            type=dialog_info["type"],
            error=error_text.replace("\n", " ")
        ))

        # Find close button
        close_selectors = [
            'button[title*="Close"]',
            'button[aria-label*="Close"]',
            'button.slds-modal__close',
            '.slds-modal__header button',
            'button:has-text("Close")'
        ]

        dialog_locator = dialog_info["locator"]
        close_btn = None

        for selector in close_selectors:
            btn = dialog_locator.locator(selector).first
            if await btn.is_visible():
                close_btn = btn
                break

        if not close_btn:
            # Fallback: ESC key
            ulog.emit("[SENTINEL] action=close_fallback method=ESC")
            await self.page.keyboard.press("Escape")
        else:
            ulog.emit("[SENTINEL] action=close_button selector={selector}".format(
                selector=close_selectors[0] if close_btn else "ESC"
            ))
            await close_btn.click()

        # Wait for dialog to disappear
        await self.page.wait_for_selector('role=dialog', state='hidden', timeout=5000)

        # Wait for DOM idle
        await self.page.wait_for_load_state("domcontentloaded")

        # Record error history
        self.error_history.append({
            "step": self.last_safe_step,
            "error": error_text,
            "type": dialog_info["type"]
        })

        # Return recovery plan
        return {
            "action": "dialog_closed",
            "error_message": error_text,
            "resume_from_step": self.last_safe_step,
            "recovery_needed": True
        }

    async def _handle_toast(self, toast_info: Dict) -> Dict:
        """
        Handle toast error (informational, non-blocking).

        Toast errors don't block execution but should be logged.
        """
        ulog.emit("[SENTINEL] action=toast_detected severity={severity} text={text}".format(
            severity=toast_info["severity"],
            text=toast_info["text"][:100].replace("\n", " ")
        ))

        return {
            "action": "toast_logged",
            "severity": toast_info["severity"],
            "message": toast_info["text"],
            "recovery_needed": False  # Toasts don't block
        }

    def mark_safe_step(self, step_index: int):
        """Mark current step as safe (for recovery purposes)."""
        self.last_safe_step = step_index

    def get_error_history(self) -> list:
        """Get history of errors encountered."""
        return self.error_history
```

### Integration Point

**File**: `backend/agents/executor.py`

```python
from backend.agents.executor_intelligence import DialogSentinel

class Executor:
    def __init__(self, page):
        self.page = page
        self.sentinel = DialogSentinel(page)

    async def execute_step(self, step, step_index):
        # Mark this step as safe before execution
        self.sentinel.mark_safe_step(step_index)

        # Execute the step (existing logic)
        result = await self._execute_action(step)

        # Check for error dialogs AFTER execution
        dialog_result = await self.sentinel.check_for_dialogs()

        if dialog_result and dialog_result.get("recovery_needed"):
            # Error dialog detected - return for recovery
            return {
                "status": "error_dialog",
                "dialog_info": dialog_result,
                "step": step_index
            }

        return result
```

### Telemetry Tags

```
[SENTINEL] action=detected type=aria_dialog error=Phone is required
[SENTINEL] action=close_button selector=button[title*="Close"]
[SENTINEL] action=dialog_closed resume_from=5
[SENTINEL] action=toast_detected severity=warning text=Duplicate record found
```

### Validation Test

**Input**:
```
Create Account "Acme" without Phone
Click Save
→ Error dialog: "Phone is required"
```

**Expected**:
```
[SENTINEL] action=detected type=slds_modal error=Phone is required
[SENTINEL] action=close_button selector=.slds-modal__close
[SENTINEL] action=dialog_closed resume_from=1
→ Executor auto-fills Phone field
→ Clicks Save again
→ SUCCESS
```

---

## Tool 2: Grid Reader ⚡ HIGH PRIORITY

### Purpose
Auto-detect Lightning grid columns at runtime and add missing columns needed for test execution.

### Problem Solved
**Before**: Test breaks if required column hidden in list view
```
Search for Account "Acme" by phone "555-0100"
→ Grid has columns: [Name, Type, Owner]
→ Phone column MISSING
→ Cannot filter/match by phone
→ Test FAILS
```

**After**: Grid Reader auto-adds missing columns
```
Search for Account "Acme" by phone "555-0100"
→ Grid Reader detects Phone column missing
→ Opens list controls (gear icon)
→ Adds Phone column
→ Saves view
→ Grid now has: [Name, Type, Owner, Phone]
→ SUCCESS
```

### Implementation

**File**: `backend/runtime/grid_reader.py` (new)

```python
from typing import Dict, List, Optional
from backend.utils.ulog import ulog

class GridReader:
    """
    Auto-detect and manage Lightning grid columns.

    Handles:
    - Column detection from header row
    - Missing column detection
    - Auto-adding columns via list controls
    - Column index mapping for row parsing
    """

    def __init__(self, page):
        self.page = page
        self.column_cache = {}  # Cache column mappings per grid

    async def read_grid_columns(
        self,
        scope: str = 'role=grid',
        required_columns: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Read grid columns and auto-add missing required columns.

        Args:
            scope: Selector for grid (default: role=grid)
            required_columns: List of column names that must be present

        Returns:
            Dict mapping column name → index
        """
        grid = self.page.locator(scope).first

        if not await grid.is_visible():
            ulog.emit("[GRID] status=not_found scope={scope}".format(scope=scope))
            return {}

        # Read header row
        column_map = await self._read_headers(grid)

        ulog.emit("[GRID] detected_columns={cols}".format(
            cols=",".join(column_map.keys())
        ))

        # Check for missing required columns
        if required_columns:
            missing = [col for col in required_columns if col not in column_map]

            if missing:
                ulog.emit("[GRID] missing_columns={cols} action=adding".format(
                    cols=",".join(missing)
                ))

                # Auto-add missing columns
                success = await self._add_columns(grid, missing)

                if success:
                    # Re-read headers after adding columns
                    column_map = await self._read_headers(grid)
                    ulog.emit("[GRID] updated_columns={cols}".format(
                        cols=",".join(column_map.keys())
                    ))

        # Cache column map
        self.column_cache[scope] = column_map

        return column_map

    async def _read_headers(self, grid) -> Dict[str, int]:
        """
        Read column headers from grid.

        Strategies:
        1. th elements (standard HTML table)
        2. role=columnheader (ARIA grids)
        3. .slds-th__action (Salesforce Lightning)
        """
        column_map = {}

        # Try standard th elements
        headers = await grid.locator('th').all()

        if headers:
            for idx, header in enumerate(headers):
                text = await header.inner_text()
                column_map[text.strip()] = idx
            return column_map

        # Try ARIA columnheader
        headers = await grid.locator('[role=columnheader]').all()

        if headers:
            for idx, header in enumerate(headers):
                text = await header.inner_text()
                column_map[text.strip()] = idx
            return column_map

        # Try Lightning-specific
        headers = await grid.locator('.slds-th__action, .slds-truncate').all()

        if headers:
            for idx, header in enumerate(headers):
                text = await header.inner_text()
                column_map[text.strip()] = idx
            return column_map

        return column_map

    async def _add_columns(self, grid, columns: List[str]) -> bool:
        """
        Add missing columns to grid via list controls.

        Steps:
        1. Find list controls button (gear icon)
        2. Click to open column selector
        3. Check boxes for missing columns
        4. Save view

        Returns:
            True if columns added successfully
        """
        # Find list controls button (multiple selectors for robustness)
        controls_selectors = [
            'button[title*="List View Controls"]',
            'button[title*="Display as"]',
            'button.slds-button_icon-border:has([data-key="settings"])',
            '.forceListViewManager button[title*="Select"]'
        ]

        controls_btn = None
        for selector in controls_selectors:
            btn = self.page.locator(selector).first
            if await btn.is_visible():
                controls_btn = btn
                break

        if not controls_btn:
            ulog.emit("[GRID] error=controls_not_found")
            return False

        # Click list controls
        await controls_btn.click()
        await self.page.wait_for_load_state("domcontentloaded")

        # Wait for column selector menu (could be dropdown or modal)
        await self.page.wait_for_selector('[role=menu], [role=dialog]', timeout=5000)

        # Look for "Select Fields to Display" or similar option
        select_fields_options = [
            'a:has-text("Select Fields to Display")',
            'button:has-text("Select Fields")',
            '[data-aura-class*="selectColumns"]'
        ]

        for selector in select_fields_options:
            option = self.page.locator(selector).first
            if await option.is_visible():
                await option.click()
                break

        # Wait for column picker modal
        await self.page.wait_for_selector('[role=dialog]', timeout=5000)

        # Find and check boxes for missing columns
        for column in columns:
            # Look for checkbox with label matching column name
            checkbox_selectors = [
                f'input[type=checkbox] + label:has-text("{column}")',
                f'label:has-text("{column}") input[type=checkbox]',
                f'//label[contains(text(), "{column}")]/preceding-sibling::input[@type="checkbox"]'
            ]

            for selector in checkbox_selectors:
                checkbox = self.page.locator(selector).first
                if await checkbox.is_visible():
                    # Check if not already checked
                    if not await checkbox.is_checked():
                        await checkbox.check()
                        ulog.emit("[GRID] action=column_added name={name}".format(name=column))
                    break

        # Click Save/Apply button
        save_selectors = [
            'button:has-text("Save")',
            'button:has-text("Apply")',
            'button[title*="Save"]'
        ]

        for selector in save_selectors:
            save_btn = self.page.locator(selector).first
            if await save_btn.is_visible():
                await save_btn.click()
                break

        # Wait for modal to close
        await self.page.wait_for_selector('[role=dialog]', state='hidden', timeout=5000)

        # Wait for grid to reload
        await self.page.wait_for_load_state("domcontentloaded")

        return True

    async def parse_row(
        self,
        row_locator,
        column_map: Dict[str, int]
    ) -> Dict[str, str]:
        """
        Parse grid row into dict using column map.

        Args:
            row_locator: Playwright locator for row
            column_map: Dict from read_grid_columns()

        Returns:
            Dict mapping column name → cell value
        """
        cells = await row_locator.locator('td, [role=gridcell]').all()

        row_data = {}
        for col_name, col_idx in column_map.items():
            if col_idx < len(cells):
                cell_text = await cells[col_idx].inner_text()
                row_data[col_name] = cell_text.strip()

        return row_data
```

### Integration Point

**File**: `backend/agents/executor.py`

```python
from backend.runtime.grid_reader import GridReader

class Executor:
    def __init__(self, page):
        self.page = page
        self.grid_reader = GridReader(page)

    async def search_in_grid(self, search_criteria: Dict):
        """
        Search for record in Lightning grid.

        Automatically ensures required columns are present.
        """
        # Determine which columns are needed for search
        required_cols = list(search_criteria.keys())  # e.g., ["Phone", "Created Date"]

        # Auto-read and add columns if missing
        column_map = await self.grid_reader.read_grid_columns(
            scope='role=grid',
            required_columns=required_cols
        )

        # Now search in grid using column_map
        # ... (existing search logic)
```

### Telemetry Tags

```
[GRID] detected_columns=Name,Type,Owner,Created Date
[GRID] missing_columns=Phone action=adding
[GRID] action=column_added name=Phone
[GRID] updated_columns=Name,Type,Owner,Phone,Created Date
```

### Validation Test

**Input**:
```
Search Accounts for "Acme" with phone "555-0100"
(List view has Phone column hidden)
```

**Expected**:
```
[GRID] detected_columns=Name,Type,Owner
[GRID] missing_columns=Phone action=adding
[GRID] action=column_added name=Phone
[GRID] updated_columns=Name,Type,Owner,Phone
→ Search succeeds using Phone column
→ SUCCESS
```

---

## Tool 3: Duplicate Disambiguator ⚡ CRITICAL

### Purpose
Use deterministic scoring to select correct row when multiple records match search criteria.

### Problem Solved
**Before**: Multiple "Acme" accounts cause test to fail or pick wrong one
```
Search for Account "Acme"
→ Found 3 matches:
  - Acme Insurance (phone: 555-0100, created: 2025-11-01)
  - Acme Corp (phone: 555-0200, created: 2025-11-05)
  - Acme LLC (phone: null, created: 2025-10-15)
→ Test picks first match (wrong one!)
→ Creates contact under wrong account
```

**After**: Duplicate Disambiguator scores rows and picks highest match
```
Search for Account "Acme" with phone "555-0100"
→ Found 3 matches
→ Scoring:
  - Acme Insurance: phone_match(3) + recency(0.9) = 3.9 ← WINNER
  - Acme Corp: phone_mismatch(0) + recency(1.0) = 1.0
  - Acme LLC: phone_null(0) + recency(0.4) = 0.4
→ Picks "Acme Insurance" (highest score)
→ SUCCESS
```

### Scoring Formula

```
score(row) = phone_match × 3 + recency × 1 + scope_match × 1

Where:
- phone_match: 3 if exact, 1 if partial, 0 if no match
- recency: 1.0 for today, decay linearly over 365 days
- scope_match: 1 if row in active tab, 0 otherwise
```

### Implementation

**File**: `backend/runtime/disambiguator.py` (new)

```python
from typing import Dict, List
from datetime import datetime, timedelta
import re
from backend.utils.ulog import ulog

class DuplicateDisambiguator:
    """
    Score-based row selection for duplicate records.

    Uses deterministic scoring formula:
    score = phone_match×3 + recency×1 + scope_match×1
    """

    def __init__(self, page):
        self.page = page

    async def disambiguate(
        self,
        rows: List,
        search_criteria: Dict,
        column_map: Dict[str, int]
    ) -> Dict:
        """
        Score all matching rows and return highest-scoring one.

        Args:
            rows: List of Playwright locators for matching rows
            search_criteria: Dict with search fields (e.g., {"name": "Acme", "phone": "555-0100"})
            column_map: Dict from GridReader (column name → index)

        Returns:
            Dict with winner row, score, and metadata
        """
        if len(rows) == 1:
            # No disambiguation needed
            return {
                "row": rows[0],
                "score": 1.0,
                "reason": "unique_match"
            }

        ulog.emit("[DUPLEX] action=scoring candidates={count}".format(count=len(rows)))

        scored_rows = []

        for row in rows:
            score_breakdown = await self._score_row(row, search_criteria, column_map)
            scored_rows.append(score_breakdown)

        # Sort by total score (descending), then by created_date (descending)
        scored_rows.sort(
            key=lambda x: (x["total_score"], x.get("created_date", "")),
            reverse=True
        )

        # Winner is highest-scoring row
        winner = scored_rows[0]

        # Emit detailed scoring
        ulog.emit("[DUPLEX] winner={name} score={score:.2f} breakdown=phone:{phone:.1f}+recency:{recency:.1f}+scope:{scope:.1f}".format(
            name=winner.get("name", "unknown"),
            score=winner["total_score"],
            phone=winner["phone_score"],
            recency=winner["recency_score"],
            scope=winner["scope_score"]
        ))

        return winner

    async def _score_row(
        self,
        row,
        search_criteria: Dict,
        column_map: Dict[str, int]
    ) -> Dict:
        """
        Calculate score for a single row.

        Returns dict with:
        - row: Playwright locator
        - total_score: Float (0-5 range)
        - phone_score: Float (0-3)
        - recency_score: Float (0-1)
        - scope_score: Float (0-1)
        - metadata: Dict with parsed cell values
        """
        # Parse row cells
        cells = await row.locator('td, [role=gridcell]').all()

        row_data = {}
        for col_name, col_idx in column_map.items():
            if col_idx < len(cells):
                row_data[col_name] = await cells[col_idx].inner_text()

        # Score component 1: Phone match (0-3 points)
        phone_score = self._score_phone(
            row_data.get("Phone", ""),
            search_criteria.get("phone", "")
        )

        # Score component 2: Recency (0-1 points)
        recency_score = self._score_recency(
            row_data.get("Created Date", "")
        )

        # Score component 3: Scope match (0-1 points)
        scope_score = await self._score_scope(row)

        total_score = phone_score + recency_score + scope_score

        return {
            "row": row,
            "total_score": total_score,
            "phone_score": phone_score,
            "recency_score": recency_score,
            "scope_score": scope_score,
            "name": row_data.get("Name", ""),
            "phone": row_data.get("Phone", ""),
            "created_date": row_data.get("Created Date", ""),
            "metadata": row_data
        }

    def _score_phone(self, row_phone: str, search_phone: str) -> float:
        """
        Score phone number match.

        Returns:
        - 3.0: Exact match
        - 1.0: Partial match (last 4 digits)
        - 0.0: No match
        """
        if not search_phone:
            return 0.0

        # Normalize phone numbers (remove formatting)
        row_phone_clean = re.sub(r'[^\d]', '', row_phone)
        search_phone_clean = re.sub(r'[^\d]', '', search_phone)

        # Exact match
        if row_phone_clean == search_phone_clean:
            return 3.0

        # Partial match (last 4 digits)
        if len(row_phone_clean) >= 4 and len(search_phone_clean) >= 4:
            if row_phone_clean[-4:] == search_phone_clean[-4:]:
                return 1.0

        return 0.0

    def _score_recency(self, created_date: str) -> float:
        """
        Score based on how recently record was created.

        Returns:
        - 1.0: Created today
        - 0.5: Created 6 months ago
        - 0.0: Created 1+ year ago
        - 0.0: Invalid/missing date
        """
        if not created_date:
            return 0.0

        try:
            # Parse date (supports multiple formats)
            # Examples: "11/7/2025", "2025-11-07", "Nov 7, 2025"
            parsed_date = self._parse_date(created_date)

            if not parsed_date:
                return 0.0

            # Calculate days old
            days_old = (datetime.now() - parsed_date).days

            # Linear decay over 365 days
            recency = max(0.0, 1.0 - (days_old / 365))

            return recency

        except Exception:
            return 0.0

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string in multiple formats.

        Supports:
        - MM/DD/YYYY
        - YYYY-MM-DD
        - Mon DD, YYYY
        """
        import dateutil.parser

        try:
            return dateutil.parser.parse(date_str)
        except:
            return None

    async def _score_scope(self, row) -> float:
        """
        Score based on whether row is in active tab/scope.

        Returns:
        - 1.0: Row is in currently active tab
        - 0.0: Row is not in active tab
        """
        # Check if row's parent tab is active
        # (Look for aria-selected=true on ancestor tab)
        try:
            active_tab = await row.evaluate("""
                (element) => {
                    let tab = element.closest('[role=tabpanel]');
                    if (tab) {
                        let tabId = tab.id;
                        let tabButton = document.querySelector(`[role=tab][aria-controls="${tabId}"]`);
                        return tabButton?.getAttribute('aria-selected') === 'true';
                    }
                    return false;
                }
            """)

            return 1.0 if active_tab else 0.0

        except:
            return 0.0  # Default to 0 if can't determine
```

### Integration Point

**File**: `backend/agents/executor.py`

```python
from backend.runtime.disambiguator import DuplicateDisambiguator

class Executor:
    def __init__(self, page):
        self.page = page
        self.disambiguator = DuplicateDisambiguator(page)

    async def search_and_select(self, search_criteria: Dict):
        """
        Search for record and select best match if duplicates found.
        """
        # Search in grid (existing logic)
        rows = await self.page.locator('role=grid role=row').all()

        # Filter rows by name match
        matching_rows = [r for r in rows if await self._matches_criteria(r, search_criteria)]

        if len(matching_rows) > 1:
            # Multiple matches - use disambiguator
            column_map = await self.grid_reader.read_grid_columns()
            result = await self.disambiguator.disambiguate(
                rows=matching_rows,
                search_criteria=search_criteria,
                column_map=column_map
            )

            # Click winner
            await result["row"].click()

        elif len(matching_rows) == 1:
            # Unique match - click it
            await matching_rows[0].click()

        else:
            # No matches - fail
            raise Exception(f"No matching rows for {search_criteria}")
```

### Telemetry Tags

```
[DUPLEX] action=scoring candidates=3
[DUPLEX] winner=Acme Insurance score=3.90 breakdown=phone:3.0+recency:0.9+scope:0.0
```

### Validation Test

**Input**:
```
Search for Account "Acme" with phone "555-0100"
(3 Acme accounts exist)
```

**Expected**:
```
[DUPLEX] action=scoring candidates=3
[DUPLEX] winner=Acme Insurance score=3.90 breakdown=phone:3.0+recency:0.9+scope:0.0
→ Clicks "Acme Insurance" row
→ Opens correct account
→ SUCCESS
```

---

## Integration Timeline - Week 9

### Day 1-2: Dialog Sentinel
- Implement DialogSentinel class
- Add error pattern detection (3 strategies)
- Integrate into Executor.execute_step()
- Test with forced error dialog (missing required field)

**Deliverable**: Error dialogs auto-closed, execution resumes

### Day 3-4: Grid Reader + Disambiguator
- Implement GridReader class
- Add column detection (3 strategies)
- Implement auto-add columns via list controls
- Implement DuplicateDisambiguator scoring
- Integrate both into Executor

**Deliverable**: Missing columns auto-added, duplicate rows scored

### Day 5: Validation + Telemetry
- Run 20-test suite with all 3 tools enabled
- Validate telemetry tags ([SENTINEL], [GRID], [DUPLEX])
- Document edge cases and limitations
- Prepare for Week 10 (Smarter Planner)

**Deliverable**: 80%+ reliability uplift proven

---

## Configuration Flags

**File**: `.env` or `backend/config/profiles.py`

```bash
# Executor Intelligence Tools (Week 9 MVP)
EXEC_DIALOG_SENTINEL=on       # Tool 1: Auto-close error dialogs
EXEC_GRID_READER=on           # Tool 2: Auto-manage grid columns
EXEC_DUPLEX=on                # Tool 3: Score-based duplicate selection

# Future tools (Week 10-11)
# EXEC_FOCUS_TYPING=on
# EXEC_SCOPED_IDLE=on
# EXEC_TOAST_AUDIT=on
# EXEC_VISION_BUMPER=guarded
# EXEC_EVIDENCE_RETRY=once
```

---

## Success Metrics (Week 9 End)

**Test Suite**: 20 runs of vague "Create Acme + John contact" spec

**Target Metrics**:
- ✅ Dialog Sentinel activations: 100% success rate (all dialogs closed)
- ✅ Grid Reader additions: 100% success rate (columns auto-added)
- ✅ Duplex selections: 95%+ accuracy (correct row chosen)
- ✅ Overall pass rate: 80%+ (up from current ~40-50%)

**Telemetry Coverage**:
- ✅ [SENTINEL] tags present in 100% of dialog scenarios
- ✅ [GRID] tags present in 100% of missing column scenarios
- ✅ [DUPLEX] tags present in 100% of multi-match scenarios

---

## Next Steps

**After Week 9 MVP ships**:
1. Week 10: Implement Track A (Smarter Planner - LSN)
2. Week 11: Add remaining executor tools (Toast Auditor, Vision Bumper)
3. Validation: 20-run suite across 3 Salesforce orgs

**Immediate Action (Today)**:
1. Create `backend/agents/executor_intelligence.py`
2. Create `backend/runtime/grid_reader.py`
3. Create `backend/runtime/disambiguator.py`
4. Wire into existing `backend/agents/executor.py`

---

**End of Executor Intelligence Core Specification**
