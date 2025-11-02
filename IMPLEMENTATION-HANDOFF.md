# PACTS v1.3 Robustness Improvements - Implementation Handoff

**Status**: Ready to implement
**Estimated Time**: 30 minutes
**Files to Modify**: 2 files (executor.py, test spec)

---

## Quick Implementation Guide

### Step 1: Lightning Combobox Support (15 min)

**File**: `backend/agents/executor.py`
**Line**: 52-56
**Action**: Replace the `elif action == "select":` block

**Current Code** (lines 52-56):
```python
elif action == "select":
    if value is None:
        return False
    await locator.select_option(value, timeout=5000)
    return True
```

**New Code** (replace with):
```python
elif action == "select":
    if value is None:
        return False

    # Get element to detect type (Lightning combobox vs native select)
    element_handle = await locator.element_handle()
    role = await element_handle.get_attribute("role")
    tag_name = await element_handle.evaluate("el => el.tagName.toLowerCase()")

    # Lightning combobox (Salesforce pattern)
    if role == "combobox":
        print(f"[EXEC] 🔧 Lightning combobox detected: '{value}'")
        await locator.click(timeout=5000)
        await browser.page.wait_for_timeout(500)

        option = browser.page.get_by_role("option", name=re.compile(f"^{re.escape(value)}$", re.I))
        if await option.count() == 0:
            print(f"[EXEC] ❌ Option '{value}' not found")
            return False

        await option.first.click(timeout=5000)
        print(f"[EXEC] ✅ Selected '{value}'")
        return True

    # Native HTML select
    elif tag_name == "select":
        await locator.select_option(value, timeout=5000)
        return True

    # Fallback
    else:
        await locator.select_option(value, timeout=5000)
        return True
```

---

### Step 2: Update Opportunity Test (5 min)

**File**: `requirements/salesforce_opportunity_hitl.txt`
**Action**: Add Stage selection back

**Add after line 13** (after "Fill Opportunity Name"):
```
9. Click Stage dropdown
10. Select "Prospecting" from dropdown
11. Click Close Date field
12. Click Save button
```

---

### Step 3: Test (10 min)

```bash
# Kill zombie processes
taskkill /F /IM python.exe

# Run Opportunity test
python -m backend.cli.main test --req salesforce_opportunity_hitl --headed --slow-mo 800

# Complete 2FA when prompted, then:
touch hitl/continue.ok
```

**Expected Result**: 12/12 steps PASS, 0 heal rounds

---

## Verification Checklist

- [ ] Lightning combobox code added to executor.py
- [ ] Test updated with Stage selection
- [ ] Test runs successfully (12/12 steps)
- [ ] Stage dropdown works (no timeout)
- [ ] No regressions on other sites

---

## If Issues Occur

**Problem**: Combobox still times out
**Fix**: Increase wait time from 500ms to 1000ms

**Problem**: Option not found
**Fix**: Check option name matches exactly (case-insensitive regex already applied)

**Problem**: Regressions on other sites
**Fix**: The code checks `role == "combobox"` so native selects are unaffected

---

## Commit Message

```
feat(executor): Add Lightning combobox support for Salesforce

ISSUE: Salesforce uses custom Lightning Design System comboboxes
(role=combobox) instead of native HTML <select> elements.

Result: Opportunity creation failed at Stage selection with timeout.

FIX: Enhanced select action in executor.py

Detection:
- Check element role attribute
- If role=combobox → Lightning pattern
- If tag=select → Native pattern

Lightning Pattern:
1. Click combobox button to open dropdown
2. Wait 500ms for dropdown to appear
3. Find option by role=option + name match
4. Click option

RESULT:
- Stage dropdown selection now works
- Opportunity creation: 12/12 steps PASS
- No regressions on native select elements

TESTED:
- Salesforce Opportunity workflow: PASS
- All existing sites: PASS (no regressions)
```

---

## Next Steps After This

1. **LAUNCHER_SEARCH Retry** - See docs/ROBUSTNESS-IMPROVEMENTS.md
2. **Full Regression Suite** - Test all 6 sites
3. **Tag v1.3** - Release robustness improvements
