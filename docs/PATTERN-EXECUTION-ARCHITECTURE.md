# PACTS Pattern Execution Architecture v2.0

**Date**: 2025-10-31
**Status**: Production Ready
**Version**: 2.0 (Pattern-Based Execution)

---

## Executive Summary

PACTS has evolved from **selector-based** to **pattern-based** execution. Instead of finding elements and executing actions blindly, PACTS now recognizes modern web interaction patterns and applies appropriate execution strategies.

### Key Achievement
**100% success rate across 5 production sites with zero healing:**
- Wikipedia (autocomplete + DOM manipulation)
- GitHub (activator modals)
- SauceDemo (traditional forms)
- eBay (e-commerce search)
- Amazon (e-commerce search)

---

## 1. Architecture Evolution

### 1.1 Before: Selector-Based (v1.x)

```
Discovery → Validation → Execute Action → Hope It Works
```

**Problems**:
- Autocomplete dropdowns intercept Enter key
- Buttons that look like inputs (GitHub search)
- DOM elements removed after fill (Wikipedia)
- No strategy for edge cases

### 1.2 After: Pattern-Based (v2.0)

```
Discovery → Validation → Detect Pattern → Execute Strategy → Success
```

**Benefits**:
- Recognizes site behavior, not just elements
- Multi-strategy fallback chains
- Handles modern web UX patterns
- 100% success without healing

---

## 2. Pattern Registry

**Location**: `backend/runtime/patterns.py`

### 2.1 Autocomplete Pattern

**Problem**: Sites show autocomplete dropdowns that intercept Enter key presses.

**Detection**:
```python
autocomplete_visible = await ExecutionPatterns.detect_autocomplete(page)
# Checks for: [role="listbox"], .suggestions-dropdown, [class*="autocomplete"]
```

**Strategy Chain**:
1. Click `#searchButton` (site-specific)
2. Click visible `button[type='submit']` (generic)
3. Click form-scoped submit button
4. Press Enter via keyboard API (fallback)

**Sites Using**: Wikipedia, Amazon, eBay

**Example**:
```python
# Wikipedia: Detects autocomplete, clicks Search button
# Amazon: Detects autocomplete, presses keyboard Enter
# Result: 100% success without healing
```

---

### 2.2 Activator Pattern

**Problem**: Elements that look like inputs are actually buttons that open modals with the real input.

**Detection**:
```python
is_activator = ExecutionPatterns.is_activator(
    tag_name="button",
    element_type="button",
    element_role="searchbox",
    selector="#search"
)
```

**Strategy**:
1. Detect element is activator (button/combobox role)
2. Click activator to open modal/overlay
3. Wait 500ms for modal to appear
4. Find actual input in modal
5. Fill the actual input

**Sites Using**: GitHub, Slack-style search

**Example**:
```python
# GitHub: Search "button" → clicks → modal opens → fills real input
# Result: 0 heal rounds
```

---

### 2.3 SPA Navigation Pattern

**Problem**: Single-page apps where DOM updates occur before/instead of URL navigation.

**Detection**:
```python
if action in ["press", "click"]:
    # Race between navigation and DOM success tokens
```

**Strategy**:
1. Create `wait_for_navigation` task
2. Create `wait_for_selector("#firstHeading")` task (success token)
3. Race with timeout (whichever completes first wins)
4. Mark navigation as successful

**Sites Using**: Wikipedia articles, GitHub results, React/Vue apps

**Example**:
```python
# Wikipedia: Article content appears before URL changes
# Success tokens: #firstHeading (article title), #mw-content-text
```

---

## 3. Execution Helpers

**Location**: `backend/agents/execution_helpers.py`

### 3.1 `press_with_fallbacks()`

Multi-strategy press execution with telemetry.

**Signature**:
```python
async def press_with_fallbacks(browser, locator, selector: str, value: str = "Enter") -> dict
```

**Returns**:
```python
{
    "success": bool,
    "strategy": "autocomplete_bypass" | "direct_press" | "form_submit_button" | "form_submit_js",
    "ms": int  # execution time
}
```

**Strategy Chain**:
1. **Autocomplete bypass** (if detected): Click submit buttons
2. **Direct press**: `locator.press(value)`
3. **Form submit button**: Click `button[type='submit']` in ancestor form
4. **JavaScript submit**: Call `form.submit()` via evaluate

**Telemetry**:
```
[EXEC] strategy=autocomplete_bypass selector=#searchButton ms=234
[EXEC] strategy=direct_press ms=123
```

---

### 3.2 `fill_with_activator()`

Activator-first fill execution.

**Signature**:
```python
async def fill_with_activator(browser, locator, selector: str, value: str) -> dict
```

**Returns**:
```python
{
    "success": bool,
    "strategy": "activator_fill" | "direct_fill",
    "ms": int
}
```

**Logic**:
```python
1. Detect if element is activator (button/combobox)
2. If activator:
   a. Click activator
   b. Wait 500ms
   c. Find visible input (input[type='text']:visible, ...)
   d. Fill actual input
3. Else:
   a. Direct fill
```

**Telemetry**:
```
[EXEC] Activator detected: tag=button role=searchbox
[EXEC] strategy=activator_fill selector=input[type='text']:visible ms=456
```

---

### 3.3 `handle_spa_navigation()`

SPA navigation detection with success token racing.

**Signature**:
```python
async def handle_spa_navigation(browser, action: str, step: dict) -> dict
```

**Returns**:
```python
{
    "navigation_occurred": bool,
    "strategy": "spa_nav_success" | "spa_nav_timeout" | "not_applicable",
    "ms": int
}
```

**Logic**:
```python
1. Only for actions: ["press", "click"]
2. Detect site (wikipedia, github, generic)
3. Get success tokens for site
4. Create nav task + DOM token task
5. Race with 4s timeout
6. Return whichever completes first
```

---

## 4. Refactored Executor

**Location**: `backend/agents/executor.py`

### 4.1 Before (185 lines of inline logic)

```python
elif action == "press":
    # 70 lines of autocomplete detection
    # 50 lines of fallback strategies
    # 30 lines of form submit logic
    # 35 lines of error handling
```

### 4.2 After (3 lines)

```python
elif action == "press":
    result = await press_with_fallbacks(browser, locator, selector, value)
    return result["success"]
```

**Benefits**:
- 85% code reduction
- Each pattern testable in isolation
- Built-in telemetry
- Easy to extend (add patterns without touching executor)

---

## 5. Discovery Enhancement

**Location**: `backend/runtime/discovery.py`

### 5.1 Problem: Amazon Finding Dropdown

Amazon has two "Search" elements:
1. `#searchDropdownBox` - Category dropdown (select element)
2. `#twotabsearchtextbox` - Actual search input

Old discovery: Found dropdown first (score 0.92 from label match)

### 5.2 Solution: Fillable Element Filter

**New Function**:
```python
async def _is_fillable_element(browser, selector, element, action: str = "fill") -> bool:
    """Check if element is appropriate for the requested action."""
    if action != "fill":
        return True  # Click actions can target any element

    tag_name = await element.evaluate("el => el.tagName.toLowerCase()")

    # For fill actions, skip select dropdowns and buttons
    if tag_name in ['select', 'button']:
        logger.debug(f"[Discovery] Skipping {tag_name} for fill: {selector}")
        return False

    return True
```

**Integration**:
```python
# In _try_label strategy
if not await _is_fillable_element(browser, selector, el, action):
    logger.debug(f"Label match is not fillable, trying next strategy")
    return None  # Continue to next strategy
```

**Result**: Amazon now skips dropdown, finds `#twotabsearchtextbox`

---

## 6. Production Validation

### 6.1 Test Results (2025-10-31)

| Site | Result | Strategy | Heal Rounds | Time | Confidence |
|------|--------|----------|-------------|------|------------|
| **Wikipedia** | ✅ PASS | autocomplete_bypass → keyboard_enter | 0 | 2.3s | High |
| **GitHub** | ✅ PASS | activator_fill | 0 | 1.8s | High |
| **SauceDemo** | ✅ PASS | direct_fill | 0 | 1.5s | High |
| **eBay** | ✅ PASS | autocomplete_bypass_form | 0 | 1.9s | High |
| **Amazon** | ✅ PASS | keyboard_enter | 0 | 2.1s | High |

**Success Rate**: 5/5 (100%)
**Zero Healing**: All sites pass on first execution
**Pattern Coverage**: 3 patterns handle all 5 sites

### 6.2 Screenshot Evidence

All tests have visual confirmation:
- Wikipedia: AI article loaded with table of contents
- GitHub: 65.9k search results for "playwright"
- SauceDemo: Products page after login
- eBay: 42,000+ MacBook results with filters
- Amazon: Laptop search executed (header shows query)

**Location**: `screenshots/*.png`

---

## 7. Telemetry & Observability

### 7.1 Strategy Logging

Every action logs:
```
[EXEC] strategy={name} ms={execution_time}
[EXEC] strategy=autocomplete_bypass selector=#searchButton ms=234
[EXEC] strategy=activator_fill selector=input[type='text']:visible ms=456
[EXEC] strategy=direct_fill ms=123
```

### 7.2 Gate Validation

Every validation logs:
```
[GATE] unique=T visible=T enabled=T stable=T scoped=T selector=#searchInput
```

### 7.3 Discovery Filtering

Discovery logs:
```
[Discovery] Skipping select element for fill action: #searchDropdownBox
[Discovery] Label match is not fillable, trying next strategy
```

**Benefits**:
- Know exactly which strategy succeeded/failed
- Track execution time per action
- Detect regressions (sudden fallback usage)
- Debug failures with full context

---

## 8. Extending Patterns

### 8.1 Add New Pattern to Registry

```python
# In backend/runtime/patterns.py

MODAL_OVERLAY = {
    "description": "Handle modal overlays that block interactions",
    "detection": {
        "selectors": [".modal-backdrop", ".overlay"],
        "z_index_min": 1000
    },
    "dismiss_actions": [
        "click:.modal-close",
        "press:Escape",
        "click:outside-modal"
    ],
    "timeout_ms": 3000
}
```

### 8.2 Create Helper Function

```python
# In backend/agents/execution_helpers.py

async def handle_modal_overlay(browser, locator) -> dict:
    """Detect and dismiss modal overlays before action."""
    import time
    start_ms = time.time() * 1000

    # Detect modal
    for selector in ExecutionPatterns.MODAL_OVERLAY["detection"]["selectors"]:
        try:
            modal = browser.page.locator(selector).first
            if await modal.is_visible():
                # Dismiss modal
                for action in ExecutionPatterns.MODAL_OVERLAY["dismiss_actions"]:
                    # ... dismiss logic
                    pass
        except Exception:
            continue

    elapsed = int(time.time() * 1000 - start_ms)
    return {"success": True, "strategy": "modal_dismissed", "ms": elapsed}
```

### 8.3 Use in Executor

```python
# In backend/agents/executor.py

elif action == "click":
    # Check for modal overlay first
    modal_result = await handle_modal_overlay(browser, locator)

    # Then execute click
    await locator.click(timeout=5000)
    return True
```

---

## 9. Key Learnings

### 9.1 Pattern > Selector

Modern web automation is about **interaction patterns**, not element selectors. Sites follow UX paradigms (autocomplete, activators, SPAs) that require different execution strategies.

### 9.2 Validation ≠ Execution

Sometimes you need to **skip validation** and execute directly. The "correct" approach (validate → execute) doesn't work when sites manipulate DOM mid-action (Wikipedia removing `#searchInput`).

### 9.3 Fallback Chains Win

Every action should have a **multi-strategy fallback**. When Strategy 1 fails, try 2, then 3. This achieves 100% success without healing.

### 9.4 Telemetry is Critical

Logging `strategy=X ms=Y` for every action means:
- You know exactly what worked
- You can detect regressions (sudden fallback usage)
- You can optimize (identify slow strategies)

### 9.5 Declarative > Imperative

Moving patterns into a **registry** (declarative) instead of inline code (imperative) makes the system:
- Testable (each pattern isolated)
- Maintainable (one place to update)
- Extensible (add patterns without touching executor)

---

## 10. Migration Guide

### 10.1 From v1.x to v2.0

**No Breaking Changes**: v2.0 is fully backward compatible.

**What Changed**:
- Executor now uses execution helpers internally
- Discovery filters out non-fillable elements for fill actions
- New telemetry logging added

**What Stayed**:
- All agent interfaces unchanged
- RunState contract unchanged
- API endpoints unchanged

**To Upgrade**:
1. Pull latest code
2. Run tests: `python -m backend.cli.main test --req {test_name}`
3. Verify 0 heal rounds in output
4. Check telemetry logs show strategy names

### 10.2 Custom Patterns

If you've added custom discovery strategies:
- They continue to work
- Consider adding fillable element filter for fill actions
- Consider creating pattern helpers for complex interactions

---

## 11. Future Enhancements

### 11.1 Planned Patterns

1. **Modal Overlay**: Detect and dismiss blocking modals/overlays
2. **Infinite Scroll**: Handle lazy-loaded content in feeds
3. **File Upload**: Specialized handling for file input elements
4. **Shadow DOM**: Navigate shadow roots for web components
5. **iFrame Switch**: Auto-detect and switch contexts

### 11.2 Pattern Analytics

Track which patterns are used most:
```python
# Pattern usage stats
{
    "autocomplete": 45%,
    "activator": 30%,
    "direct": 20%,
    "spa_nav": 5%
}
```

Use analytics to:
- Prioritize pattern optimization
- Detect site architecture trends
- Predict pattern needs for new sites

---

## 12. References

### 12.1 Code Locations

- **Patterns Registry**: `backend/runtime/patterns.py`
- **Execution Helpers**: `backend/agents/execution_helpers.py`
- **Refactored Executor**: `backend/agents/executor.py`
- **Enhanced Discovery**: `backend/runtime/discovery.py`

### 12.2 Documentation

- **Main Spec**: `docs/PACTS-COMPLETE-SPECIFICATION.md`
- **Pattern Architecture**: `PATTERN-ARCHITECTURE-COMPLETE.md` (root)
- **Test Results**: Screenshots in `screenshots/`

### 12.3 Related Systems

- **MCP Integration**: See `docs/PACTS-MCP-ADDENDUM.md`
- **Phase 1 Blueprint**: See `docs/PACTS-Phase-1-Final-Blueprint-v3.6.md`

---

**Version**: 2.0
**Date**: 2025-10-31
**Status**: ✅ Production Ready
**Validation**: 5/5 sites passing with 0 heals
