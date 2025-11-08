# PACTS Phase C: Intelligent Agent Architecture

**Status**: SPECIFICATION (Not Yet Implemented)
**Timeline**: Week 9-11 (3 weeks)
**Goal**: Transform PACTS from selector automation → intelligent test agent
**Last Updated**: 2025-11-07

---

## Executive Summary

**The Problem**: PACTS currently requires perfect test specifications and deterministic execution paths. Real-world business users write vague, incomplete test cases like:

```
"Create an account Acme and add a contact John. Then verify it shows."
```

Current PACTS would fail because:
- Missing required fields (Phone, Email)
- Ambiguous "verify it shows" (shows where? how?)
- Duplicate risk (what if "Acme" already exists?)
- No disambiguation strategy (multiple Johns, multiple Acmes)

**The Solution**: Two-track upgrade that makes PACTS work with **messy reality**:

1. **Track A**: Smarter Planner (Loose-Spec Normalizer) - Fill gaps BEFORE execution
2. **Track B**: Executor Intelligence (Runtime Adaptation) - Handle chaos DURING execution

---

## Track A: Loose-Spec Normalizer (LSN)

**File**: `backend/agents/planner_lsn.py` (new)

### Purpose

Transform vague, incomplete test steps into deterministic execution plans with:
- Auto-filled missing fields
- Inferred disambiguation strategies
- Extracted constraints and success criteria
- Risk detection and mitigation

### Example Transformation

**Input** (messy user spec):
```
Create an account Acme and add a contact John. Then verify it shows.
```

**Output** (normalized intent JSON):
```json
{
  "entities": [
    {"type": "Account", "fields": {"name": "Acme", "phone": "555-0100", "email": "acme@example.com"}},
    {"type": "Contact", "fields": {"first_name": "John", "last_name": "Doe", "phone": "555-0101", "email": "john.doe.1731048123@example.com"}}
  ],
  "required_fields": {
    "Account": ["name", "phone"],
    "Contact": ["first_name", "last_name", "email"]
  },
  "search_strategy": {
    "filters": ["phone", "created_date"],
    "sort": "created_date_desc",
    "tiebreak": "recency"
  },
  "success_asserts": [
    {"type": "toast_present", "text_contains": "created"},
    {"type": "related_list_row", "field": "email", "value": "john.doe.*@example.com"}
  ],
  "disambiguation_plan": {
    "duplicate_detection": true,
    "filter_by": ["phone", "created_date"],
    "score_weights": {"phone_match": 3, "recency": 1, "scope_match": 1}
  }
}
```

### LSN Components

#### 1. Constraint Extractor
**Purpose**: Parse natural language into structured entities

```python
def extract_constraints(text: str) -> Dict[str, Any]:
    """
    Extract entities, intents, and relationships from vague test description.

    Maps:
    - Nouns → Entities (Account, Contact, Opportunity)
    - Verbs → Intents (create, search, open, verify, delete)
    - Locations → Scopes (Tab: Accounts, Related: Contacts, Dialog: New Opportunity)
    """
    # Use LLM with structured output
    prompt = f"""
    Extract structured test intent from this vague description:

    "{text}"

    Identify:
    1. Entities (objects to create/modify)
    2. Intents (actions to perform)
    3. Scopes (UI locations)
    4. Assertions (verification steps)
    """

    # Returns structured JSON with entities + intents
```

#### 2. Ambiguity Detector
**Purpose**: Identify potential duplicate/collision risks

```python
def detect_ambiguities(entities: List[Dict]) -> List[Dict]:
    """
    Detect potential issues that could cause test failures.

    Checks:
    - Duplicate risk (name collisions)
    - Missing required fields
    - Vague assertions ("verify it shows")
    - Non-unique identifiers
    """
    ambiguities = []

    for entity in entities:
        # Check for duplicate risk
        if "name" in entity and is_common_name(entity["name"]):
            ambiguities.append({
                "type": "duplicate_risk",
                "entity": entity["type"],
                "field": "name",
                "value": entity["name"],
                "mitigation": "add_phone_filter + created_date_sort"
            })

        # Check for missing required fields
        required = get_required_fields(entity["type"])
        missing = [f for f in required if f not in entity["fields"]]
        if missing:
            ambiguities.append({
                "type": "missing_fields",
                "entity": entity["type"],
                "fields": missing,
                "mitigation": "auto_generate_defaults"
            })

    return ambiguities
```

#### 3. Field Auto-Filler
**Purpose**: Generate smart defaults for missing required fields

```python
def auto_fill_fields(entity: Dict) -> Dict:
    """
    Auto-generate missing required fields with deterministic defaults.

    Rules:
    - Phone: Generate unique 10-digit (555-01XX format)
    - Email: {entity.name}.{timestamp}@example.com
    - Website: https://{entity.name}.example.com
    - Date fields: Use consistent defaults (CloseDate = +30 days)
    """
    import time
    timestamp = int(time.time())

    defaults = {
        "phone": f"555-{timestamp % 10000:04d}",
        "email": f"{entity['name'].lower()}.{timestamp}@example.com",
        "website": f"https://{entity['name'].lower()}.example.com",
        "close_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    }

    for field, default in defaults.items():
        if field not in entity.get("fields", {}):
            entity["fields"][field] = default

    return entity
```

#### 4. Selector Strategy Generator
**Purpose**: Emit ranked list of locators for each intent

```python
def generate_selector_strategies(intent: Dict) -> List[Dict]:
    """
    For each intent, emit ranked selector strategies.

    Priority:
    1. [stable aria|data-*] - Stable ARIA labels or test IDs
    2. role+text - ARIA roles with text matching
    3. relational(css: within grid/section) - CSS within specific containers
    4. vision(glyph/text) - OCR as last resort

    Returns list of strategies to try in order.
    """
    strategies = []

    if intent["type"] == "fill":
        strategies = [
            {"tier": 1, "strategy": "aria-label", "selector": f"input[aria-label*='{intent['element']}']"},
            {"tier": 2, "strategy": "placeholder", "selector": f"input[placeholder*='{intent['element']}']"},
            {"tier": 3, "strategy": "label-for", "selector": f"label:has-text('{intent['element']}') >> input"},
            {"tier": 4, "strategy": "vision", "selector": f"ocr_nearby_input(text='{intent['element']}')"}
        ]

    return strategies
```

#### 5. Self-Questions Engine (No Human in Loop)
**Purpose**: Auto-answer disambiguation questions using heuristics

```python
def self_question(question: str, context: Dict) -> Dict:
    """
    Auto-answer ambiguity questions using deterministic policies.

    Examples:
    Q: "Duplicate risk detected—use phone filter?"
    A: auto: yes (always add phone filter for duplicate risk)

    Q: "Toast captured—use URL for confirmation only?"
    A: auto: yes (toast is primary, URL is backup)

    Q: "Multiple rows match Name—use recency sort?"
    A: auto: yes (always prefer latest when ambiguous)
    """
    policies = {
        "duplicate_risk": {"use_phone_filter": True, "use_recency_sort": True},
        "toast_confirmation": {"primary": "toast", "backup": "url"},
        "multiple_matches": {"tiebreak": "created_date_desc"}
    }

    # Match question to policy and auto-answer
    for policy_name, policy in policies.items():
        if policy_name in question.lower():
            return {"answer": policy, "confidence": 0.95}

    # Default: conservative (fail-safe)
    return {"answer": "ask_user", "confidence": 0.0}
```

---

## Track B: Executor Intelligence Tools

**File**: `backend/agents/executor_intelligence.py` (new)

### Purpose

Give executor "eyes and reflexes" to adapt to real-world chaos during execution.

### Tool 1: Universal Dialog Sentinel ✅ HIGH PRIORITY

**Purpose**: Auto-close error dialogs and resume execution

```python
async def dialog_sentinel(page, last_safe_step: int):
    """
    Watch for Salesforce error dialogs and auto-close them.

    Detects:
    - role=dialog with error indicators
    - Lightning toast errors
    - Known SF error banners

    Policy:
    - Close dialog
    - Wait for DOM idle
    - Resume from last_safe_step
    """
    # Check for error dialog
    error_dialog = await page.locator('role=dialog').filter(has_text=re.compile(r'error|invalid|required|duplicate', re.I)).first

    if await error_dialog.is_visible():
        # Log error message
        error_text = await error_dialog.inner_text()
        ulog.executor(event="error_dialog_detected", message=error_text[:100])

        # Find and click close button
        close_btn = error_dialog.locator('button[title*="Close"], button:has-text("Close")')
        await close_btn.click()

        # Wait for dialog to disappear
        await page.wait_for_load_state("domcontentloaded")

        ulog.executor(event="error_dialog_closed", resumed_from=last_safe_step)

        return {"action": "closed", "error": error_text, "resume_step": last_safe_step}
```

**Feature Toggle**: `EXEC_DIALOG_SENTINEL=on`

### Tool 2: Deterministic List Reader ✅ HIGH PRIORITY

**Purpose**: Auto-detect Lightning grid columns at runtime

```python
async def read_grid_columns(page, scope="role=grid"):
    """
    Detect Lightning grid columns and their mappings.

    If required columns missing:
    - Open list controls (gear icon)
    - Add missing columns
    - Save view

    Returns column mappings for row parsing.
    """
    grid = page.locator(scope)

    # Read header row
    headers = await grid.locator('th, [role=columnheader]').all_text_contents()

    # Map column names to indices
    column_map = {header.strip(): idx for idx, header in enumerate(headers)}

    # Check for required columns
    required = ["Phone", "Created Date"]
    missing = [col for col in required if col not in column_map]

    if missing:
        ulog.executor(event="grid_columns_missing", columns=missing)

        # Auto-add columns via list controls
        await add_grid_columns(page, missing)

        # Re-read headers
        headers = await grid.locator('th').all_text_contents()
        column_map = {header.strip(): idx for idx, header in enumerate(headers)}

    return column_map
```

**Feature Toggle**: `EXEC_GRID_READER=on`

### Tool 3: Duplicate Disambiguator ✅ CRITICAL

**Purpose**: Score-based row selection when multiple matches exist

```python
async def disambiguate_duplicate_rows(page, search_criteria: Dict, scope="role=grid"):
    """
    When multiple rows match Name, use scoring to pick the right one.

    Score formula:
    score(row) = exact_match(phone)*3 + recency(created_date)*1 + scope_match(tab)*1

    Click highest score. If tie → latest created_date.
    """
    grid = page.locator(scope)
    rows = await grid.locator('tr[role=row]').all()

    scored_rows = []

    for row in rows:
        score = 0
        cells = await row.locator('td').all()

        # Extract cell values
        name = await cells[0].inner_text()
        phone = await cells[1].inner_text() if len(cells) > 1 else ""
        created_date = await cells[2].inner_text() if len(cells) > 2 else ""

        # Score: phone match (exact = 3 points)
        if phone == search_criteria.get("phone"):
            score += 3

        # Score: recency (parse date, newer = 1 point)
        if created_date:
            days_old = (datetime.now() - parse_date(created_date)).days
            score += max(0, 1 - days_old / 365)  # Decay over 1 year

        # Score: scope match (current tab = 1 point)
        if await is_in_active_tab(row):
            score += 1

        scored_rows.append({"row": row, "score": score, "name": name, "phone": phone, "date": created_date})

    # Sort by score (desc), then by created_date (desc)
    scored_rows.sort(key=lambda x: (x["score"], x["date"]), reverse=True)

    winner = scored_rows[0]
    ulog.executor(event="disambiguated", winner=winner["name"], score=winner["score"])

    # Click the winning row
    await winner["row"].click()
```

**Feature Toggle**: `EXEC_DUPLEX=on`

### Tool 4: Focus-Aware Typing

**Purpose**: Handle Lightning hydration/focus issues

```python
async def fill_with_focus_awareness(page, selector: str, value: str):
    """
    Prefer :focus target, else the input paired with label text.

    Handles:
    - Lightning inputs that gain focus during hydration
    - Label-input pairing mismatches
    - Async-loaded comboboxes
    """
    # Check if an input is already focused
    focused = page.locator(':focus')
    if await focused.is_visible() and await focused.get_attribute('type') in ['text', 'email', 'tel']:
        await focused.fill(value)
        ulog.executor(event="fill_focused_input", selector=":focus")
        return

    # Otherwise use provided selector
    await page.locator(selector).fill(value)
```

**Feature Toggle**: `EXEC_FOCUS_TYPING=on`

### Tool 5: Adaptive Idle (Scoped Wait)

**Purpose**: Wait for specific regions instead of whole page

```python
async def wait_scoped_idle(page, scope="role=grid"):
    """
    Wait for visible, interactive region to be idle (not whole page).

    Bound to:
    - role=grid (list views)
    - role=dialog (modals)
    - [data-aura-rendered-by] (Lightning components)
    """
    scope_el = page.locator(scope)

    # Wait for scope to be visible
    await scope_el.wait_for(state="visible", timeout=10000)

    # Wait for no DOM mutations within scope for 500ms
    await page.evaluate(f"""
        new Promise(resolve => {{
            const target = document.querySelector('{scope}');
            const observer = new MutationObserver(() => {{
                clearTimeout(timer);
                timer = setTimeout(() => {{
                    observer.disconnect();
                    resolve();
                }}, 500);
            }});
            let timer = setTimeout(() => {{
                observer.disconnect();
                resolve();
            }}, 500);
            observer.observe(target, {{childList: true, subtree: true}});
        }})
    """)
```

**Feature Toggle**: `EXEC_SCOPED_IDLE=on`

### Tool 6: Toast Auditor (Non-Nav Confirmation)

**Purpose**: Confirm success from toast, use URL as backup

```python
async def audit_toast_confirmation(page, expected_text: str):
    """
    Capture success confirmation from Lightning toast.

    Primary: Toast text contains expected_text
    Backup: URL contains record ID

    Returns record_id if found.
    """
    # Wait for toast
    toast = page.locator('.slds-notify--toast, [role=alert]')

    if await toast.is_visible():
        text = await toast.inner_text()

        if expected_text.lower() in text.lower():
            ulog.executor(event="toast_confirmed", text=text[:50])

            # Extract record ID from toast or URL
            record_id = extract_record_id(text) or extract_record_id_from_url(page.url)

            return {"confirmed": True, "source": "toast", "record_id": record_id}

    # Fallback: Check URL for record ID
    if "/r/" in page.url:
        record_id = extract_record_id_from_url(page.url)
        ulog.executor(event="url_confirmed", record_id=record_id)
        return {"confirmed": True, "source": "url", "record_id": record_id}

    return {"confirmed": False}
```

**Feature Toggle**: `EXEC_TOAST_AUDIT=on`

### Tool 7: Vision Bumper (Guarded Last Resort)

**Purpose**: OCR column headers when CSS selectors fail

```python
async def vision_bumper_grid_headers(page, scope="role=grid"):
    """
    When CSS changes break grid headers, OCR the header strip.

    Only engages when:
    - CSS selectors return 0 results
    - Grid is visible but unreadable

    Uses Tesseract OCR to read header text from screenshot.
    """
    grid = page.locator(scope)

    # Take screenshot of header row only
    header_row = grid.locator('thead, [role=row]:first-child')
    screenshot = await header_row.screenshot()

    # OCR the screenshot
    import pytesseract
    from PIL import Image
    import io

    image = Image.open(io.BytesIO(screenshot))
    text = pytesseract.image_to_string(image)

    # Parse column names
    columns = text.split('\t')  # Tesseract uses tabs for columns
    column_map = {col.strip(): idx for idx, col in enumerate(columns)}

    ulog.executor(event="vision_ocr_headers", columns=list(column_map.keys()))

    return column_map
```

**Feature Toggle**: `EXEC_VISION_BUMPER=guarded` (only when CSS fails)

### Tool 8: Evidence-Driven Retries

**Purpose**: Change one variable and retry on failure

```python
async def evidence_retry(page, failed_intent: Dict, failure_type: str):
    """
    On failure, change exactly one variable and retry once.

    Strategies:
    - Filter op: equals → contains
    - Sort: asc → desc
    - Scope: grid → related_list
    - Timeout: 5s → 10s
    """
    retry_strategies = {
        "selector_not_found": [
            {"change": "scope", "from": "page", "to": "role=dialog"},
            {"change": "tier", "from": "aria-label", "to": "role-name"}
        ],
        "multiple_matches": [
            {"change": "filter_op", "from": "equals", "to": "contains"},
            {"change": "sort", "from": "asc", "to": "desc"}
        ],
        "timeout": [
            {"change": "wait_strategy", "from": "networkidle", "to": "domcontentloaded"},
            {"change": "timeout", "from": 5000, "to": 10000}
        ]
    }

    strategies = retry_strategies.get(failure_type, [])

    for strategy in strategies[:1]:  # Try only 1 retry
        ulog.executor(event="evidence_retry", strategy=strategy)

        # Apply change and retry
        modified_intent = apply_strategy(failed_intent, strategy)
        result = await execute_intent(page, modified_intent)

        if result["success"]:
            return result

    return {"success": False, "retries_exhausted": True}
```

**Feature Toggle**: `EXEC_EVIDENCE_RETRY=once`

---

## Configuration: enterprise_loose Profile

**File**: `.env` (or `backend/config/profiles.py`)

```bash
# Enable Loose-Spec Normalizer (Track A)
PLANNER_PROFILE=enterprise_loose
LSN_AUTO_FILL_FIELDS=true
LSN_AMBIGUITY_DETECTOR=true
LSN_SELF_QUESTIONS=auto  # No human in loop

# Enable Executor Intelligence Tools (Track B)
EXEC_DIALOG_SENTINEL=on
EXEC_GRID_READER=on
EXEC_DUPLEX=on  # duplicate disambiguator
EXEC_FOCUS_TYPING=on
EXEC_SCOPED_IDLE=on
EXEC_TOAST_AUDIT=on
EXEC_VISION_BUMPER=guarded  # Only when CSS fails
EXEC_EVIDENCE_RETRY=once
```

---

## Validation Test Plan

### Test 1: Vague Account + Contact Creation
**Input** (messy):
```
Create an account Acme and add a contact John. Then verify it shows.
```

**Expected Behavior**:
1. LSN fills Phone (555-XXXX) and Email (acme.{timestamp}@example.com)
2. LSN adds disambiguation plan (phone filter + recency sort)
3. Executor creates Account
4. Executor navigates to Contacts related list
5. Executor creates Contact with auto-generated email
6. Dialog Sentinel closes any error dialogs
7. Toast Auditor confirms "Contact created"
8. Duplicate Disambiguator scores rows if multiple Johns exist

**Pass Criteria**: ✅ PASS with 0 manual intervention

### Test 2: Duplicate Account Handling
**Input**:
```
Create account "Acme Insurance" with phone 555-0100
```
(Run twice to test duplicate detection)

**Expected Behavior**:
1. First run: Creates Account successfully
2. Second run: LSN detects duplicate risk
3. Executor auto-adds phone filter to search
4. Duplicate Disambiguator scores existing Acme (phone match = 3 points)
5. Test detects duplicate and either:
   - Updates existing (if intent is "ensure exists")
   - Skips creation (if intent is "create new unique")

**Pass Criteria**: ✅ PASS - deterministic handling of duplicates

### Test 3: Error Dialog Recovery
**Input**:
```
Create opportunity "Big Deal" with close date tomorrow
```
(Salesforce will show error: "Close date cannot be in past")

**Expected Behavior**:
1. Executor fills form with tomorrow's date
2. Clicks Save
3. Dialog Sentinel detects error dialog
4. Reads error message: "Close date cannot be in past"
5. Closes dialog
6. Evidence Retry adjusts close_date = +1 day
7. Re-submits form
8. Toast Auditor confirms success

**Pass Criteria**: ✅ PASS with 1 auto-retry

### Test 4: Grid Column Auto-Management
**Input**:
```
Find account "Acme" by phone 555-0100
```
(Org has Phone column hidden in default view)

**Expected Behavior**:
1. Grid Reader detects Phone column missing
2. Opens list controls (gear icon)
3. Adds Phone column
4. Saves view
5. Re-reads grid with Phone column visible
6. Duplicate Disambiguator uses phone to match row

**Pass Criteria**: ✅ PASS - auto-adds missing column

---

## Implementation Roadmap

### Week 9: Track A (Smarter Planner)
**Days 1-2**: Constraint Extractor + Ambiguity Detector
**Days 3-4**: Field Auto-Filler + Self-Questions Engine
**Day 5**: Selector Strategy Generator + Integration

**Files to Create**:
- `backend/agents/planner_lsn.py`
- `backend/utils/field_defaults.py`
- `backend/agents/self_questions.py`

### Week 10: Track B (Executor Intelligence)
**Days 1-2**: Dialog Sentinel + Grid Reader
**Days 3-4**: Duplicate Disambiguator + Focus Typing
**Day 5**: Scoped Idle + Toast Auditor

**Files to Create**:
- `backend/agents/executor_intelligence.py`
- `backend/runtime/grid_reader.py`
- `backend/runtime/disambiguator.py`

### Week 11: Vision + Evidence Retry + Validation
**Days 1-2**: Vision Bumper (OCR integration)
**Days 3-4**: Evidence Retry + Integration testing
**Day 5**: 20-run validation suite

**Files to Create**:
- `backend/runtime/vision_ocr.py`
- `backend/agents/evidence_retry.py`

---

## Success Criteria

**Loose-Spec Handling**:
- ✅ Vague test "Create Acme account" → deterministic execution (auto-fills 3+ fields)
- ✅ Ambiguous "verify it shows" → concrete assertion (toast OR URL)
- ✅ Duplicate risk auto-detected and mitigated (phone filter + recency)

**Runtime Intelligence**:
- ✅ Error dialogs auto-closed with 100% success rate
- ✅ Duplicate rows disambiguated with 95%+ accuracy
- ✅ Grid columns auto-managed (missing columns added)
- ✅ Focus/hydration issues handled (0 timing failures)

**Validation**:
- ✅ 20 consecutive runs of vague account+contact test = 100% pass rate
- ✅ 0 manual intervention required
- ✅ Average execution time < 45 seconds (with all tools enabled)

---

## Phase C vs Browser-Use Comparison

| Capability | PACTS Phase C | Browser-Use |
|-----------|---------------|-------------|
| **Vague spec handling** | LSN fills gaps | Interprets naturally |
| **Duplicate detection** | Score-based (phone×3 + recency) | Vision-based similarity |
| **Error recovery** | Dialog Sentinel + Evidence Retry | Vision + LLM replanning |
| **Grid reading** | CSS + OCR fallback | Vision-first |
| **Speed** | Fast (CSS selectors) | Slower (vision inference) |
| **Cost** | Low (minimal LLM calls) | Higher (vision model per step) |
| **Determinism** | High (policy-driven) | Medium (LLM-driven) |

**Recommendation**: Start with Phase C (Track A+B) for 80% of cases. Add browser-use integration for the 20% where pure vision is needed (e.g., unlabeled buttons, dynamic layouts).

---

## Next Steps

1. **Review and approve this spec** - Confirm Track A+B approach
2. **Prioritize tools** - Which of the 8 executor tools are must-haves for Week 10?
3. **Start Week 9** - Implement LSN (Constraint Extractor + Field Auto-Filler)
4. **Validation plan** - Define the 20-run test suite for vague account+contact creation

---

**End of Phase C Specification**
