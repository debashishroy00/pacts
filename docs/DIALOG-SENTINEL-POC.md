# Dialog Sentinel POC - Implementation Summary

**Status**: IMPLEMENTED (Ready for Validation)
**Date**: 2025-11-07
**Feature Flag**: `PACTS_SENTINEL_FEATURE=true`
**Timeline**: 90-minute POC (as planned)

---

## What Was Built

### 1. DialogSentinel Class (`backend/agents/dialog_sentinel.py`)

**Full implementation** with 3 detection strategies:
- **ARIA dialog**: `role=dialog` with error keywords
- **SLDS modal**: `.slds-modal.slds-fade-in-open` (Salesforce Lightning)
- **Force modal**: `[data-aura-class*="forceModalDialog"]` (legacy)

**Error Pattern Matching** (11 keywords):
```python
ERROR_PATTERNS = [
    r'required', r'invalid', r'duplicate', r'already exists',
    r'cannot be', r'must be', r'must have', r'error', r'failed',
    r'missing', r'not allowed'
]
```

**Auto-Close Logic**:
- Tries 6 different close button selectors
- Falls back to ESC key if no button found
- Waits for dialog to disappear (3s timeout)
- Waits for DOM to settle

### 2. Executor Integration (`backend/agents/executor.py`)

**Two Hook Points**:

**Hook 1 - BEFORE Step** (line 319):
```python
# Week 9 Phase C POC: Check for stray error dialogs BEFORE starting step
# This clears any modals left over from previous steps
await sentinel.check_and_close()
```

**Hook 2 - AFTER Action** (lines 485-494):
```python
# Week 9 Phase C POC: Check for error dialogs AFTER actions that can trigger saves/navigation
# This catches Salesforce validation errors (e.g., "Phone is required")
if action in ("click", "press"):
    dialog_result = await sentinel.check_and_close()
    if dialog_result:
        # Error dialog was closed - action needs retry or healing
        logger.warning(f"[SENTINEL] Dialog detected after {action}: {dialog_result.get('error_message', '')[:100]}")
        # Mark as timeout so healing can retry with corrected data
        state.failure = Failure.timeout
        return state
```

### 3. Telemetry Integration (`metrics_collector.py`)

**New Regex Pattern**:
```python
SENTINEL_RE = re.compile(r"\[SENTINEL\].*?action=(?P<action>detected|close_button|esc_fallback)")
```

**New Counter**:
```python
"sentinel_actions": Counter(),  # detected, close_button, esc_fallback
```

**Integration**: Tracks all sentinel actions across test runs for metrics reporting.

---

## Feature Toggle

**Environment Variable**: `PACTS_SENTINEL_FEATURE`

**Values**:
- `"true"` - Sentinel enabled (POC validation mode)
- `"false"` - Sentinel disabled (default, zero blast radius)

**Implementation**:
```python
self.enabled = os.getenv("PACTS_SENTINEL_FEATURE", "false").lower() == "true"
```

If disabled, `check_and_close()` returns `None` immediately - **zero codepath changes**.

---

## Expected Telemetry Output

When sentinel detects and closes an error dialog:

```
[SENTINEL] action=detected type=slds_modal error=Phone is required. Please provide a phone number.
[SENTINEL] action=close_button selector=button[title*="Close"]
```

When using ESC fallback:
```
[SENTINEL] action=detected type=aria_dialog error=Invalid email format
[SENTINEL] action=esc_fallback
```

---

## Validation Test Plan

### Test 1: Simple Contact Creation (Current Run)
**Command**:
```bash
PACTS_SENTINEL_FEATURE=true python -m backend.cli.main test --req salesforce_create_contact --clear-cache
```

**Expected Behavior**:
1. Test runs normally
2. If any error dialogs appear, sentinel detects them
3. Sentinel closes dialogs automatically
4. Test either succeeds or enters healing with clean slate

**Success Criteria**:
- ✅ Test completes (PASS or FAIL with healing)
- ✅ No manual intervention needed
- ✅ [SENTINEL] tags present if dialogs encountered
- ✅ No [READINESS] Stage 2 ❌ on DISCOVERY_FAILED after Save

### Test 2: Complex Contact+Account Test (Next)
**Command**:
```bash
PACTS_SENTINEL_FEATURE=true python -m backend.cli.main test --req salesforce_contact_account --clear-cache
```

**Expected Behavior**:
1. Test creates Account
2. If validation error (e.g., duplicate, missing field), sentinel closes dialog
3. Test retries via healing
4. Creates Contact associated with Account

**Success Criteria**:
- ✅ Pass rate ≥ 2/2 consecutive runs
- ✅ Heal rounds ≤ 1 (ideally 0)
- ✅ [SENTINEL] detection count matches number of error dialogs

---

## POC Success Criteria (90-Minute Target)

### Technical Implementation ✅ COMPLETE
- ✅ DialogSentinel class with 3 detection strategies
- ✅ Error pattern matching (11 keywords)
- ✅ Auto-close logic (6 selectors + ESC fallback)
- ✅ Feature toggle (PACTS_SENTINEL_FEATURE)
- ✅ Executor integration (2 hook points)
- ✅ Telemetry integration (metrics_collector)

### Validation (In Progress)
- ⏳ Run 1: salesforce_create_contact (RUNNING)
- ⏳ Run 2: salesforce_create_contact (back-to-back)
- ⏳ Analyze logs for [SENTINEL] tags
- ⏳ Verify pass rate improvement

### Go/No-Go Decision Criteria

**GO** (Green-light Week 9 full build):
- ✅ Sentinel detects error dialogs (logged)
- ✅ Sentinel closes dialogs successfully
- ✅ Tests proceed after dialog closure (no DISCOVERY_FAILED)
- ✅ Pass rate ≥ 2/2 for simple Contact test

**NO-GO** (Pivot to Grid Reader next):
- ❌ Sentinel never triggers (no error dialogs in this flow)
- ❌ Sentinel fails to close dialogs (still blocks tests)
- ❌ Pass rate same as baseline (sentinel provides no value)

---

## Implementation Timeline (Actual)

**Total Time**: ~90 minutes (as planned)

| Task | Time | Status |
|------|------|--------|
| Create DialogSentinel class | 30 min | ✅ |
| Wire into executor.py | 20 min | ✅ |
| Add telemetry integration | 15 min | ✅ |
| Write documentation | 10 min | ✅ |
| Run validation test | 15 min | ⏳ |
| **TOTAL** | **90 min** | **ON TRACK** |

---

## Next Steps

### If POC Succeeds (Expected)
1. **Week 9 Day 1-2**: Complete Dialog Sentinel refinement
   - Add more error patterns based on validation logs
   - Improve close button selector coverage
   - Add retry logic for stubborn dialogs

2. **Week 9 Day 3-4**: Implement Grid Reader + Disambiguator
   - Column detection and auto-add logic
   - Phone×3 + recency×1 scoring
   - Integration with executor

3. **Week 9 Day 5**: Full validation suite
   - 20-run test on vague "Create Acme + John" spec
   - Target: 80%+ pass rate

### If POC Partially Succeeds
- Sentinel works but edge cases found → Refine and re-test
- Timeline: Add 1-2 days for hardening before Grid Reader

### If POC Fails (Unlikely)
- Pivot to Grid Reader immediately (missing columns more critical)
- Return to Dialog Sentinel after Grid Reader proven

---

## Code Locations

**New Files**:
- `backend/agents/dialog_sentinel.py` (200 lines)

**Modified Files**:
- `backend/agents/executor.py` (added import + 2 hooks, ~20 lines)
- `metrics_collector.py` (added SENTINEL_RE pattern + Counter tracking, ~15 lines)

**Zero Blast Radius**: When `PACTS_SENTINEL_FEATURE=false`, all sentinel code is bypassed - no impact on existing tests.

---

## Telemetry Examples (Expected)

### Scenario 1: Clean Run (No Errors)
```
[EXEC] URL=https://...salesforce.com ...
[PROFILE] using=DYNAMIC detail=sf-lightning
[READINESS] stage=dom-idle info=-
[GATE] unique=True visible=True enabled=True stable=True scoped=True
→ No [SENTINEL] tags (no error dialogs)
[RESULT] status=PASS
```

### Scenario 2: Error Dialog Detected
```
[EXEC] URL=https://...salesforce.com ...
[PROFILE] using=DYNAMIC detail=sf-lightning
[READINESS] stage=dom-idle info=-
[GATE] unique=True visible=True enabled=True stable=True scoped=True
[SENTINEL] action=detected type=slds_modal error=Phone is required
[SENTINEL] action=close_button selector=button.slds-modal__close
→ Test proceeds to healing (Failure.timeout)
[HEAL] ⚠️ Retry attempt 1/3
→ Healing fills Phone field
→ Retry Save action
[RESULT] status=PASS steps=9 heals=1
```

---

**End of POC Summary**
