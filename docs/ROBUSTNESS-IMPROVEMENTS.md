# PACTS Robustness Improvements Plan

**Date**: 2025-11-02
**Status**: READY FOR IMPLEMENTATION
**Version**: v1.3 (Post v1.2-prod-validated)

---

## Executive Summary

Based on comprehensive testing of 6 production sites (5 at 100%, Salesforce Opportunity at 50-73%), we've identified two critical improvements needed for Salesforce robustness:

1. **Lightning Combobox Support** - Handle Salesforce custom dropdowns
2. **LAUNCHER_SEARCH Reliability** - Add retry logic for transient failures

---

## Priority 1: Lightning Combobox Support

### Problem Statement
**Issue**: Salesforce uses custom Lightning Design System comboboxes (role=combobox) instead of native HTML `<select>` elements.

**Current Behavior**:
```python
# In executor.py line 52-56
elif action == "select":
    if value is None:
        return False
    await locator.select_option(value, timeout=5000)  # ← Fails on comboboxes
    return True
```

**Impact**: Opportunity creation fails at step 8 (Stage selection) with timeout error.

### Solution Design

**Detection Strategy**:
```python
# Check if element is a Lightning combobox vs native select
element_handle = await locator.element_handle()
role = await element_handle.get_attribute("role")
tag_name = await element_handle.evaluate("el => el.tagName.toLowerCase()")

is_lightning_combobox = (role == "combobox")
is_native_select = (tag_name == "select")
```

**Lightning Combobox Pattern**:
```python
# Step 1: Click combobox button to open dropdown
await locator.click(timeout=5000)

# Step 2: Wait for dropdown menu to appear
await browser.page.wait_for_timeout(500)

# Step 3: Find and click the option
option_locator = browser.page.get_by_role("option", name=re.compile(f"^{re.escape(value)}$", re.I))
await option_locator.first.click(timeout=5000)

print(f"[EXEC] ✅ Lightning combobox: selected '{value}'")
```

### Implementation

**File**: `backend/agents/executor.py`

**Changes**:
```python
elif action == "select":
    if value is None:
        return False

    # Get element to detect type
    element_handle = await locator.element_handle()
    role = await element_handle.get_attribute("role")
    tag_name = await element_handle.evaluate("el => el.tagName.toLowerCase()")

    # Lightning combobox (Salesforce pattern)
    if role == "combobox":
        print(f"[EXEC] 🔧 Detected Lightning combobox, using click-then-select pattern")

        # Click to open dropdown
        await locator.click(timeout=5000)

        # Wait for dropdown to appear
        await browser.page.wait_for_timeout(500)

        # Find and click the option
        option_locator = browser.page.get_by_role("option", name=re.compile(f"^{re.escape(value)}$", re.I))
        option_count = await option_locator.count()

        if option_count == 0:
            print(f"[EXEC] ❌ Option '{value}' not found in combobox dropdown")
            return False

        await option_locator.first.click(timeout=5000)
        print(f"[EXEC] ✅ Lightning combobox: selected '{value}'")
        return True

    # Native HTML select element
    elif tag_name == "select":
        await locator.select_option(value, timeout=5000)
        return True

    # Unknown select type
    else:
        print(f"[EXEC] ⚠️ Unknown select element: role={role}, tag={tag_name}")
        # Try native select as fallback
        await locator.select_option(value, timeout=5000)
        return True
```

### Testing

**Test Case**: Salesforce Opportunity Creation with Stage selection

**Test Steps**:
1. Fill Opportunity Name → ✅
2. Select "Prospecting" from Stage dropdown → **Should work with fix**
3. Click Close Date → ✅
4. Click Save → ✅

**Expected Result**: Opportunity created successfully (10/10 steps, 0 heal rounds)

---

## Priority 2: LAUNCHER_SEARCH Reliability

### Problem Statement
**Issue**: LAUNCHER_SEARCH succeeds 50% of the time, depending on which page Salesforce lands on after 2FA.

**Test 1** (Success):
- After 2FA: Landed on `/lightning/o/Contact/pipelineInspection`
- LAUNCHER_SEARCH for Opportunities: ✅ SUCCESS

**Test 2** (Failure):
- After 2FA: Landed on `/lightning` (home page)
- LAUNCHER_SEARCH for Opportunities: ❌ TIMEOUT

**Root Cause**: App Launcher dialog may not be immediately available or may timeout on first attempt.

### Solution Design

**Retry Strategy**:
```python
MAX_LAUNCHER_RETRIES = 2

for retry in range(MAX_LAUNCHER_RETRIES):
    try:
        # Existing LAUNCHER_SEARCH logic
        ...
        break  # Success, exit retry loop

    except Exception as e:
        if retry < MAX_LAUNCHER_RETRIES - 1:
            print(f"[EXEC] ⚠️ Launcher search retry {retry+1}/{MAX_LAUNCHER_RETRIES} for: {target}")

            # Close App Launcher and reopen (fresh state)
            await browser.page.keyboard.press("Escape")
            await browser.page.wait_for_timeout(500)

            # Reopen App Launcher
            app_launcher_button = browser.page.get_by_role("button", name=re.compile("app.?launcher", re.I))
            await app_launcher_button.first.click()
            await browser.page.wait_for_timeout(1000)

            continue  # Try again
        else:
            # Final retry failed
            print(f"[EXEC] ❌ Launcher search failed after {MAX_LAUNCHER_RETRIES} retries: {target}")
            print(f"[EXEC] Diagnostics: url={browser.page.url}")
            raise e
```

### Implementation

**File**: `backend/agents/executor.py`

**Location**: LAUNCHER_SEARCH section (around line 220-275)

**Changes**:
```python
# LAUNCHER_SEARCH pattern (special Salesforce selector)
if selector.startswith("LAUNCHER_SEARCH:"):
    target = selector.split(":", 1)[1]
    print(f"[EXEC] Launcher search detected for: {target}")

    MAX_LAUNCHER_RETRIES = 2
    last_error = None

    for retry_attempt in range(MAX_LAUNCHER_RETRIES):
        try:
            # Find App Launcher panel
            panel = browser.page.get_by_role("dialog", name=re.compile("app.?launcher", re.I))
            panel_count = await panel.count()

            if panel_count == 0:
                raise Exception(f"App Launcher panel not found (retry {retry_attempt+1}/{MAX_LAUNCHER_RETRIES})")

            # Use search box
            search = panel.get_by_role("combobox", name=re.compile("search", re.I)).first
            await search.fill(target)

            # Get current URL before pressing Enter
            old_url = browser.page.url

            await browser.page.keyboard.press("Enter")

            # Wait for navigation to complete
            try:
                await browser.page.wait_for_load_state("networkidle", timeout=3000)
            except:
                pass

            # Check if we navigated to the target
            new_url = browser.page.url
            navigated_to_object = (
                new_url != old_url and (
                    "/lightning/o/" in new_url or
                    "/lightning/r/" in new_url or
                    "/lightning/page/" in new_url
                ) and target.lower() in new_url.lower()
            )

            if navigated_to_object:
                print(f"[EXEC] ✅ Launcher search auto-navigated to: {target} ({new_url})")
                break  # Success
            else:
                # Try clicking result button
                result_button = panel.get_by_role("button", name=re.compile(f"^{re.escape(target)}$", re.I))
                button_count = await result_button.count()

                if button_count > 0:
                    await result_button.first.click(timeout=5000)
                    print(f"[EXEC] ✅ Clicked launcher result button for: {target}")
                    break  # Success
                else:
                    raise Exception(f"No results found for '{target}' in App Launcher")

        except Exception as e:
            last_error = e

            if retry_attempt < MAX_LAUNCHER_RETRIES - 1:
                # Retry logic
                print(f"[EXEC] ⚠️ Launcher search retry {retry_attempt+1}/{MAX_LAUNCHER_RETRIES} for: {target}")

                # Close and reopen App Launcher
                await browser.page.keyboard.press("Escape")
                await browser.page.wait_for_timeout(500)

                app_launcher_button = browser.page.get_by_role("button", name=re.compile("app.?launcher", re.I))
                await app_launcher_button.first.click()
                await browser.page.wait_for_timeout(1000)

                continue  # Try again
            else:
                # Final retry failed
                print(f"[EXEC] ❌ Launcher search failed after {MAX_LAUNCHER_RETRIES} retries: {target}")
                print(f"[EXEC] Diagnostics: url={browser.page.url}, last_error={str(last_error)}")
                raise last_error

    print(f"[EXEC] Launcher search succeeded for: {target}")
    # Rest of execution flow...
```

### Testing

**Test Case**: Salesforce Opportunity Creation (full workflow)

**Expected Behavior**:
- First attempt may timeout → Automatically retry
- Second attempt should succeed
- Total time: <10 seconds (including retry)

**Success Criteria**:
- 90%+ success rate on LAUNCHER_SEARCH (up from 50%)
- 0-1 retry attempts average

---

## Implementation Checklist

### Phase 1: Lightning Combobox Support
- [ ] Read current executor.py select action implementation
- [ ] Add combobox detection logic
- [ ] Implement click-then-select pattern
- [ ] Add error handling and logging
- [ ] Test with Salesforce Opportunity Stage dropdown
- [ ] Verify no regressions on native select elements

### Phase 2: LAUNCHER_SEARCH Reliability
- [ ] Read current LAUNCHER_SEARCH implementation
- [ ] Add retry loop with MAX_LAUNCHER_RETRIES=2
- [ ] Implement close/reopen App Launcher logic
- [ ] Add enhanced error diagnostics
- [ ] Test with Salesforce Opportunity workflow
- [ ] Verify no regressions on Contacts workflow

### Phase 3: Testing & Validation
- [ ] Run full regression suite (5 sites)
- [ ] Run Salesforce Contacts workflow (15 steps)
- [ ] Run Salesforce Opportunity workflow (10-11 steps)
- [ ] Verify 0 heal rounds on all tests
- [ ] Document success rates and metrics

### Phase 4: Documentation & Release
- [ ] Update CHANGELOG.md with v1.3 improvements
- [ ] Update SALESFORCE-FIXES-SUMMARY.md
- [ ] Create commit with detailed description
- [ ] Update version to v1.3-robustness-improvements
- [ ] Push to GitHub

---

## Success Metrics

### Before (v1.2)
- Salesforce Opportunity: 50-73% success
- LAUNCHER_SEARCH reliability: 50%
- Lightning combobox: 0% (timeout)

### After (v1.3) - Target
- Salesforce Opportunity: 90%+ success
- LAUNCHER_SEARCH reliability: 90%+
- Lightning combobox: 90%+ (new feature)

### KPIs
- Overall success rate: 100% (6/6 sites)
- Heal rounds average: 0
- Execution time: <2s per step

---

## Risk Assessment

**Risk Level**: LOW

**Backward Compatibility**: ✅ HIGH
- Changes are additive (new patterns, not modifications)
- Existing native select behavior preserved
- Retry logic only activates on failure

**Testing Coverage**: ✅ COMPREHENSIVE
- 5 existing sites for regression
- 2 Salesforce workflows for validation
- Clear success criteria

**Rollback Plan**: ✅ AVAILABLE
- Git revert to v1.2-prod-validated if issues arise
- No database changes, purely runtime logic

---

## Next Steps

1. **Review this plan** - Validate approach with stakeholders
2. **Implement Phase 1** - Lightning combobox support
3. **Implement Phase 2** - LAUNCHER_SEARCH retry logic
4. **Test Phase 3** - Full regression + Salesforce validation
5. **Release Phase 4** - Commit, tag, and push v1.3

**Estimated Effort**: 2-3 hours implementation + 1 hour testing = **3-4 hours total**

**Go/No-Go Decision**: Ready to proceed? (Y/N)
