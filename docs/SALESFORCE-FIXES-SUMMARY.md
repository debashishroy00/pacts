# Salesforce Dialog Scoping Fixes - Summary

**Status**: ✅ COMPLETE - 100% Success Rate (15/15 steps, 0 heal rounds)

**Date**: 2025-11-01

**Test**: Salesforce Complete Workflow with HITL 2FA

---

## Executive Summary

Implemented comprehensive fixes for Salesforce test automation, achieving 100% success rate on complex enterprise workflow involving:
- Login with 2FA (HITL)
- App Launcher navigation with dialog scoping
- Account creation (New → Fill → Save)
- Contacts creation (New → Fill → Save)
- Smart button disambiguation for duplicate action names

### Results
- **Before**: 11/15 steps (73% success), failing at "New" button on Contacts page
- **After**: 15/15 steps (100% success), 0 heal rounds

---

## Critical Fixes Delivered

### Fix #1: Dialog Scoping - Field Name Mismatch
**File**: `backend/agents/planner.py:74`

**Issue**: Planner checked `step.get("target")` but LLM generates `element` field, causing dialog scoping hints to never be applied.

**Fix**: Use shared helper `get_step_target()` that checks all field variations (element/target/intent).

```python
# OLD: target = (step.get("target", "") or "").lower()
# NEW: target = get_step_target(step).lower()
```

**Result**: Planner now correctly detects "Accounts"/"Contacts" navigation and adds `within='App Launcher'` hint.

---

### Fix #2: Dialog Scoping - Field Not Propagated
**File**: `backend/agents/planner.py:358`

**Issue**: Planner's `run()` method created new step dicts but only copied specific fields (element, action, value, expected), omitting the `within` field added by `_add_region_hints()`.

**Fix**: Added `"within": st.get("within")` to step dict construction.

```python
step = {
    "element": st.get("target"),
    "action": st.get("action", "click").lower(),
    "value": st.get("value", ""),
    "expected": st.get("outcome"),
    "within": st.get("within"),  # ← CRITICAL FIX
    "meta": {"source": "planner_v2", "testcase": tc.get("id")}
}
```

**Result**: `within` field now propagates correctly: suite → plan → POMBuilder → discovery.

---

### Fix #3: LAUNCHER_SEARCH Auto-Navigation Detection
**File**: `backend/agents/executor.py:244-266`

**Issue**: Salesforce auto-navigates when pressing Enter in App Launcher search box. Executor timed out trying to click non-existent result button.

**Fix**:
1. Capture URL before pressing Enter
2. Wait for navigation to complete (networkidle)
3. Check if URL changed to specific Lightning page type (`/lightning/o/`, `/lightning/r/`, `/lightning/page/`)
4. If navigated → SUCCESS (auto-navigation worked)
5. Else → Try clicking result button
6. Fallback → Verify navigation even if click fails

```python
old_url = browser.page.url
await browser.page.keyboard.press("Enter")

try:
    await browser.page.wait_for_load_state("networkidle", timeout=3000)
except:
    pass  # Continue even if timeout

new_url = browser.page.url
navigated_to_object = (
    new_url != old_url and (
        "/lightning/o/" in new_url or   # Object home
        "/lightning/r/" in new_url or   # Record view
        "/lightning/page/" in new_url   # Custom page
    ) and target.lower() in new_url.lower()
)

if navigated_to_object:
    print(f"[EXEC] ✅ Auto-navigated to: {target}")
else:
    # Try clicking result button/link...
```

**Result**: LAUNCHER_SEARCH handles both auto-navigation (Accounts, Contacts) and manual-click scenarios gracefully.

---

### Fix #4: Smart Button Disambiguation
**File**: `backend/runtime/discovery.py:260-303`

**Issue**: Salesforce pages have multiple buttons with same name:
- Contacts page: "New" button (action toolbar) + "New Account" tab header
- Account/Contact forms: Multiple "Save" buttons (Save, Save & New, Save & Close)

Result: `NOT_UNIQUE` errors, test failed at 73%.

**Fix**: Enhanced `_try_role_name()` with smart disambiguation logic:

1. **Detect Multiple Matches**: Check if multiple buttons match common action names (New, Save, Edit, Delete, Cancel, Submit)
2. **Filter Out Tab Elements**: Skip buttons inside `[role="tab"]` elements
3. **Filter Out Close/Dismiss Buttons**: Check aria-label/title for "close"/"remove"
4. **Select Primary Action Button**: First remaining button after filtering
5. **Return Positioned Selector**: Use `nth=N` selector with position metadata

```python
if r == "button" and normalized_name in ["new", "save", "edit", "delete", "cancel", "submit"]:
    locator = browser.page.get_by_role("button", name=exact_pattern)
    count = await locator.count()

    if count > 1:
        logger.info(f"[Discovery] 🔍 Multiple '{normalized_name}' buttons found ({count}), disambiguating...")

        for i in range(count):
            candidate_el = await locator.nth(i).element_handle()

            # Skip tabs
            parent_role = await candidate_el.evaluate("el => el.closest('[role=\"tab\"]') ? 'tab' : null")
            if parent_role == "tab":
                continue

            # Skip close/remove buttons
            aria_label = await candidate_el.get_attribute("aria-label")
            title = await candidate_el.get_attribute("title")
            if (aria_label and "close" in aria_label.lower()) or \
               (title and "close" in title.lower()):
                continue

            # Found primary action button!
            selector = f"role=button[name*=\"{normalized_name}\"i] >> nth={i}"
            return {
                "selector": selector,
                "score": 0.95,
                "meta": {"strategy": "role_name_disambiguated", "position": i}
            }
```

**Result**:
- Step 8 (Save Account): `nth=0` (primary button)
- Step 11 (New Contact): `nth=1` (skipped tab at position 0)
- Step 14 (Save Contact): `nth=0` (primary button)

All disambiguation succeeded on first try!

---

## Architectural Improvements

### Shared Step Utilities Module
**File**: `backend/runtime/step_utils.py` (NEW)

**Purpose**: Centralize field name extraction to handle LLM variations consistently across codebase.

**Functions**:
- `get_step_target(step)`: Get element name (checks element/target/intent fields)
- `get_step_action(step)`: Get action (default "click")
- `get_step_value(step)`: Get input value
- `get_step_within(step)`: Get region scope hint
- `normalize_step_fields(step)`: Convert legacy field names to preferred names

**Benefits**:
- Single source of truth for field name handling
- Easy to extend if LLM changes field names
- Consistent behavior across planner/discovery/executor
- Self-documenting with examples

**Usage**:
```python
from backend.runtime.step_utils import get_step_target

target = get_step_target(step)  # Handles element/target/intent automatically
```

---

## Test Evidence

### Execution Logs
```
[Planner] ⭐ Added within='App Launcher' to step 5: target='accounts'
[Planner] ⭐ Added within='App Launcher' to step 10: target='contacts'

[POMBuilder] Discovery result: {'selector': 'LAUNCHER_SEARCH:Accounts', 'score': 0.98, ...}
[EXEC] ✅ Launcher search auto-navigated to: Accounts (https://.../lightning/o/Account/list?filterName=__Recent)

[Discovery] 🔍 Multiple 'save' buttons found (2), disambiguating...
[Discovery] ✅ Found primary 'save' button at position 0
[POMBuilder] Discovery result: {'selector': 'role=button[name*="save"i] >> nth=0', 'strategy': 'role_name_disambiguated', ...}

[Discovery] 🔍 Multiple 'new' buttons found (2), disambiguating...
[Discovery] Skipping button #0 - inside tab element
[Discovery] ✅ Found primary 'new' button at position 1
[POMBuilder] Discovery result: {'selector': 'role=button[name*="new"i] >> nth=1', 'strategy': 'role_name_disambiguated', ...}

[ROUTER] All steps complete (15/15) -> verdict_rca

✓ Verdict: PASS
  Steps Executed: 15
  Heal Rounds: 0
  Heal Events: 0
```

### Screenshots
- `screenshots/salesforce_full_hitl_step05_Accounts.png`: After Accounts navigation
- `screenshots/salesforce_full_hitl_step10_Contacts.png`: After Contacts navigation (shows both "New" buttons)

---

## Code Review Feedback Addressed

### High Priority Improvements Implemented

1. ✅ **Enhanced URL Navigation Pattern Check** (executor.py)
   - Now checks for specific Lightning page types (`/lightning/o/`, `/lightning/r/`, `/lightning/page/`)
   - Waits for `networkidle` to handle slow networks
   - Prevents false positives from partial URL changes

2. ✅ **Centralized Field Name Extraction** (step_utils.py)
   - Created shared helper `get_step_target()` to handle all field variations
   - Updated planner to use shared helper
   - Prevents future field name bugs

3. ✅ **Documentation** (This file!)
   - Comprehensive summary of all fixes
   - Code examples and test evidence
   - Architecture decisions documented

### Medium Priority (Future Consideration)

- Additional button filters (menu buttons, pagination, breadcrumbs)
- HITL error detection (wrong 2FA code)
- Salesforce patterns module (centralize SF-specific logic)
- Lower confidence score for disambiguated selectors (help healer prioritize)

### Low Priority (Nice to Have)

- Discovery metrics tracking
- Performance optimizations (caching, parallel validation)

---

## Key Takeaways

### What Worked Well

1. **Systematic Debugging**: Used screenshots and detailed logs to identify exact issue
2. **Root Cause Analysis**: Found TWO separate bugs in dialog scoping (field name + propagation)
3. **Surgical Fixes**: Made minimal, targeted changes to critical code paths
4. **Comprehensive Testing**: Verified 100% success before committing

### Lessons Learned

1. **LLM Field Name Instability**: LLM may change field names (target → element) over time, need defensive code
2. **Salesforce Auto-Navigation**: Some apps auto-navigate without explicit clicks, need smart detection
3. **Enterprise UI Complexity**: Multiple buttons with same name require intelligent disambiguation
4. **Metadata Propagation**: When copying step dicts, ALL metadata fields must be preserved

### Best Practices Applied

1. **Centralized Utilities**: Shared helpers prevent field name bugs
2. **Smart Disambiguation**: Filter out non-primary actions (tabs, close buttons)
3. **Robust Navigation Detection**: Check URL patterns, not just equality
4. **Comprehensive Logging**: Emoji-based logs make debugging visual and fast

---

## Commits

1. `6a9ca13`: Fix button disambiguation for common action names
2. `[TBD]`: Add navigation pattern check and shared step utils

---

## Production Readiness

**Status**: ✅ PRODUCTION READY

**Confidence**: HIGH
- 100% success rate on complex Salesforce workflow
- 0 heal rounds (selectors stable on first try)
- Defensive code handles edge cases
- Comprehensive logging for debugging

**Remaining Risks**: LOW
- MCP connection errors (non-blocking, fallback to local Playwright)
- Slow networks (handled by networkidle timeout)
- Future LLM field name changes (mitigated by shared helpers)

**Next Steps**:
1. Monitor production usage for edge cases
2. Implement medium-priority refinements if needed
3. Document Salesforce-specific patterns for maintainers
