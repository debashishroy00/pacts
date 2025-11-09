# Week 9 Dialog Sentinel Validation Report

**Date**: 2025-11-08
**Test**: Salesforce Contact + Account Creation
**Feature**: Dialog Sentinel (Phase C POC)
**Status**: ⚠️ FALSE POSITIVE DETECTED

---

## Executive Summary

Dialog Sentinel successfully detects and closes dialogs, but **incorrectly identifies legitimate create modals as error dialogs**. The POC needs refinement to distinguish between:

1. **Legitimate modals** (e.g., "New Account" form) - should remain open
2. **Error dialogs** (e.g., "Phone is required" validation) - should be closed

---

## Test Results

### Option 1: Sentinel After-Action Only
**Command**: `PACTS_SENTINEL_FEATURE=true PACTS_SENTINEL_BEFORE_STEP=off PACTS_SENTINEL_AFTER_ACTION=on`

**Result**: ❌ FAIL at step 4/21 (Account Name)

**Root Cause**:
```
[SENTINEL] action=detected type=aria_dialog error=Cancel and close New Account * = Required Information...
[SENTINEL] action=close_button selector=button.slds-modal__close
```

The Sentinel detected the legitimate "New Account" modal because it contains the text "* = Required Information", which matches the `required` keyword in ERROR_PATTERNS.

**Impact**: Modal closed immediately after clicking "New" button, preventing field entry.

---

### Option 2: Sentinel Disabled (Baseline)
**Command**: `PACTS_SENTINEL_FEATURE=false`

**Result**: ❌ FAIL at step 12/20 (Search...)

**Progress**: Got further (12 steps vs 4), successfully:
- Opened App Launcher
- Searched for Accounts
- Clicked "New"
- Filled all Account fields (Name, Type, Industry, Country, Phone, Website)
- Clicked "Save"

**Root Cause**: Different issue - test failed while trying to navigate back to Accounts tab after Save. Logs show:
```
[Discovery] 🔍   Button 0: 'Close error dialog' (visible=True)
```

This suggests an actual error dialog appeared after Save (possibly validation error), but without Sentinel enabled, the test couldn't recover.

**Key Insight**: Sentinel disabled allows legitimate modals to work, but test still fails when real error dialogs appear.

---

## Technical Analysis

### Sentinel Integration Points

The Sentinel is currently called in two places ([executor.py](backend/agents/executor.py)):

1. **Line 319**: Before EVERY step
   ```python
   # Week 9 Phase C POC: Check for stray error dialogs BEFORE starting step
   await sentinel.check_and_close()
   ```

2. **Line 488**: After click/press actions
   ```python
   if action in ("click", "press"):
       dialog_result = await sentinel.check_and_close()
   ```

### False Positive Mechanism

The "New Account" modal triggers false positive because:

1. Modal opens with role=dialog
2. Modal contains text: "* = Required Information"
3. Sentinel's `_has_error_keywords()` matches on `required` keyword
4. Sentinel closes the modal assuming it's an error

### Error Pattern List

Current patterns ([dialog_sentinel.py:32-44](backend/agents/dialog_sentinel.py#L32-L44)):
```python
ERROR_PATTERNS = [
    r'required',        # ← FALSE POSITIVE TRIGGER
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
```

---

## Recommendations

### 1. Add Positive Indicators Filter (Recommended)

Don't close dialogs that contain **create/form indicators**:

```python
# Add to DialogSentinel class
LEGITIMATE_MODAL_INDICATORS = [
    r'new account',
    r'new contact',
    r'new opportunity',
    r'create',
    r'edit',
    r'account information',
    r'contact information',
    r'cancel and close',  # Legitimate close button text
]

def _has_error_keywords(self, text: str) -> bool:
    """Check if text contains error keywords AND NOT legitimate modal indicators."""
    if not text:
        return False

    text_lower = text.lower()

    # First check if it's a legitimate modal
    if any(re.search(pattern, text_lower) for pattern in self.LEGITIMATE_MODAL_INDICATORS):
        return False  # Don't treat as error

    # Then check for error keywords
    return any(re.search(pattern, text_lower) for pattern in self.ERROR_PATTERNS)
```

### 2. Refine "Required" Pattern

Change from broad `r'required'` to more specific error patterns:

```python
ERROR_PATTERNS = [
    r'is required',       # "Phone is required"
    r'field is required', # "This field is required"
    r'required field',    # "Missing required field"
    # Keep other patterns
    r'invalid',
    r'duplicate',
    # ...
]
```

### 3. Add Context-Aware Timing

Only check for error dialogs **after actions that can trigger validation**:

```python
# In executor.py
# Remove line 319 (before-step check)
# Keep line 488 (after click/press)

# Add smarter check after Save actions
if action == "click" and "save" in step_name.lower():
    # Wait for potential validation errors
    await asyncio.sleep(1)
    dialog_result = await sentinel.check_and_close()
```

### 4. Add Visual Error Indicators

Check for Salesforce-specific error indicators:

```python
async def _check_aria_dialog(self) -> Optional[Dict]:
    # ... existing code ...

    # Additional check: Look for error icon
    error_icon = dialog.locator('[data-key="error"], .slds-icon-utility-error')
    has_error_icon = await error_icon.is_visible(timeout=100)

    # Only treat as error if BOTH keywords AND visual indicator present
    if not (self._has_error_keywords(text) and has_error_icon):
        return None
```

---

## Files & Artifacts

### Logs
- [runs/salesforce/sentinel_after_actions.log](runs/salesforce/sentinel_after_actions.log) - Option 1 (216 lines)
- [runs/salesforce/no_sentinel.log](runs/salesforce/no_sentinel.log) - Option 2 (329 lines)

### Screenshots
- 31 Salesforce screenshots captured in [screenshots/](screenshots/)
- Key screenshots:
  - `salesforce_contact_account.txt_step03_New.png` - Before modal opens
  - `salesforce_contact_account.txt_step04_Account_Name.png` - After Sentinel closed modal (Option 1)
  - `salesforce_contact_account.txt_step10_Save.png` - Account creation (Option 2)

### Metrics Summary
- **Overall pass rate**: 45.0% (9/20 runs)
- **Salesforce runs**: 17 total, 6 passes, 11 fails
- **Stable selector ratio**: 100.0%
- **Average heal rounds**: 2.25 per run
- Full report: [metrics_summary.md](metrics_summary.md)

---

## Next Steps

### Immediate (Same Session)
1. Implement **Recommendation #1** (positive indicators filter)
2. Implement **Recommendation #2** (refine "required" pattern)
3. Re-run validation with updated Sentinel
4. Confirm: "New Account" modal stays open, actual error dialogs are closed

### Week 9 Continuation
1. Add telemetry for false positive rate
2. Test across multiple Salesforce objects (Contact, Opportunity, Case)
3. Document known legitimate modal patterns
4. Add configuration flag for positive indicator list

---

## Configuration Used

```bash
# Option 1
PACTS_SENTINEL_FEATURE=true
PACTS_SENTINEL_BEFORE_STEP=off
PACTS_SENTINEL_AFTER_ACTION=on
PACTS_DYNAMIC_IDLE_MS=12000

# Option 2
PACTS_SENTINEL_FEATURE=false
PACTS_DYNAMIC_IDLE_MS=12000
```

**Note**: The `PACTS_SENTINEL_BEFORE_STEP` and `PACTS_SENTINEL_AFTER_ACTION` flags are **NOT currently implemented** in the code. The Sentinel runs at both integration points regardless of these flags.

---

## Conclusion

**Status**: ⚠️ Sentinel POC partially working, needs refinement

**One-liner**: "FAIL with after-action sentinel due to false positive on 'New Account' modal; Sentinel correctly detects dialogs but needs positive indicator filter to distinguish legitimate modals from error dialogs"

**Next Action**: Implement positive indicators filter (5-line code change) and re-validate.

---

**Generated by**: Claude Code
**Test Environment**: Docker (Windows host)
**Salesforce Org**: orgfarm-9a1de3d5e8-dev-ed.develop.my.salesforce.com
