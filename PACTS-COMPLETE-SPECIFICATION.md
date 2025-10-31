# PACTS - Complete System Specification v1.0

**Production-Ready Autonomous Context Testing System**

_Authoritative specification for building PACTS from ground up_

---

## Document Purpose

This is the **definitive specification** for PACTS (Production-Ready Autonomous Context Testing System). Any AI code assistant (Claude Code, GitHub Copilot, Cursor) should be able to build a complete, working PACTS implementation using only this document.

**Target Reader**: AI code assistants building PACTS from scratch
**Style**: Precise specifications, not status updates
**Completeness**: Everything needed to replicate PACTS

---

## Table of Contents

1. [System Vision & Philosophy](#1-system-vision--philosophy)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Agent Specifications](#4-agent-specifications)
5. [Discovery Strategies](#5-discovery-strategies)
6. [Five-Point Actionability Gate](#6-five-point-actionability-gate)
7. [LangGraph Orchestration](#7-langgraph-orchestration)
8. [Data Contracts](#8-data-contracts)
9. [Memory & Persistence](#9-memory--persistence)
10. [API Specifications](#10-api-specifications)
11. [Testing Requirements](#11-testing-requirements)
12. [Deployment Architecture](#12-deployment-architecture)

---

## 1. System Vision & Philosophy

### 1.1 Core Problem

Traditional test automation requires:
- Manual selector creation (brittle, time-consuming)
- Hard-coded element locators (break on UI changes)
- No autonomous healing (tests fail, require manual fixes)
- No context awareness (blind execution)

### 1.2 PACTS Solution

**Find-First Verification™**: Discover and verify selectors BEFORE generating test code

**Autonomous Healing**: Self-correct failures during execution

**Context-Aware**: Understand what's being tested, not just execute steps

### 1.3 Design Principles

1. **Deterministic**: Same input → same output (no LLM hallucinations in core logic)
2. **Observable**: Every decision traced and explainable
3. **Autonomous**: Heals failures without human intervention
4. **Production-Grade**: Built for enterprise reliability, not demos

### 1.4 Key Differentiators

| Feature | Traditional Tools | PACTS |
|---------|------------------|-------|
| Selector Discovery | Manual | Autonomous (90%+ coverage) |
| Failure Handling | Test fails | Self-heals (3 attempts) |
| Test Generation | Write code first | Verify first, generate after |
| Maintenance | High (brittle selectors) | Low (adaptive discovery) |
| Trust | Black box | Full observability |

---

## 2. Architecture Overview

### 2.1 Six-Agent Pipeline

```
┌──────────┐
│ Planner  │  Parse requirements → intents
└────┬─────┘
     │
     ▼
┌────────────┐
│ POMBuilder │  Discover selectors (Find-First)
└─────┬──────┘
      │
      ▼
┌───────────┐
│ Generator │  Generate test.py with verified selectors
└─────┬─────┘
      │
      ▼
┌──────────┐
│ Executor │  Execute actions + five-point gate
└────┬─────┘
     │
     ├──→ (on failure) ──┐
     │                   ▼
     │            ┌──────────────┐
     │            │OracleHealer  │  Self-heal (max 3 rounds)
     │            └──────┬───────┘
     │                   │
     │◄──────────────────┘
     │
     ▼
┌─────────────┐
│ VerdictRCA  │  Verdict + Root Cause Analysis
└─────────────┘
```

### 2.2 Agent Responsibilities

| Agent | Input | Output | Purpose |
|-------|-------|--------|---------|
| **Planner** | Excel/JSON requirements | Normalized intents | Parse & validate test cases |
| **POMBuilder** | Intents | Verified selectors | Discover elements (Find-First) |
| **Generator** | Verified plan | test_*.py files | Generate runnable Playwright tests |
| **Executor** | Test plan | Execution results | Run actions with validation |
| **OracleHealer** | Failures | Healed selectors | Autonomous failure recovery |
| **VerdictRCA** | All results | Verdict + RCA | Classify outcomes, analyze failures |

### 2.3 Information Flow

```
Requirements (Excel/JSON)
    ↓ Planner
Intents (normalized steps)
    ↓ POMBuilder
Verified Selectors (with confidence scores)
    ↓ Generator
Test Code (test_*.py)
    ↓ Executor
Execution Results (pass/fail per step)
    ↓ OracleHealer (if failures)
Healed Results
    ↓ VerdictRCA
Final Verdict + RCA Report
```

---

## 3. Technology Stack

### 3.1 Core Stack (Required)

| Component | Version | Purpose | Non-Negotiable |
|-----------|---------|---------|----------------|
| Python | 3.11+ | Runtime | Yes |
| LangGraph | >=1.0.0,<2.0.0 | Orchestration | Yes |
| Playwright | >=1.45,<2.0 | Browser automation | Yes (async mode) |
| Pydantic | >=2.6,<3.0 | Data validation | Yes |
| FastAPI | Latest | REST API | Yes |
| Postgres | 15+ | Persistent storage | Yes |
| Redis | 7+ | Caching & state | Yes |

### 3.2 Supporting Libraries

| Library | Purpose |
|---------|---------|
| langsmith | Observability & tracing |
| tenacity | Retry policies |
| structlog | Structured logging |
| alembic | Database migrations |
| python-dotenv | Environment config |
| jinja2 | Test code templating |

### 3.3 Why These Choices?

**LangGraph 1.0**: Deterministic state machine with checkpointing
**Playwright Async**: Non-blocking browser automation
**Pydantic**: Type-safe state management
**Postgres + Redis**: Durable state + fast caching

---

## 4. Agent Specifications

### 4.1 Planner Agent

**File**: `backend/agents/planner.py`

**Signature**:
```python
@traced("planner")
async def run(state: RunState) -> RunState:
    """Parse Excel/JSON requirements into normalized intents."""
```

**Input Format** (Excel or JSON):
```
Element@Region | Action | Value | Expected Outcome
Username@LoginForm | fill | standard_user | field_populated
Password@LoginForm | fill | secret_sauce | field_populated
Login@LoginForm | click | | navigates_to:Products
```

**Parsing Logic**:
1. Split by `|` delimiter
2. Parse `Element@Region` (region is optional)
3. Extract action, value, expected outcome
4. Create intent object per step

**Output** (to `state.context["intents"]`):
```python
[
    {
        "intent": "Username@LoginForm",
        "element": "Username",
        "region": "LoginForm",
        "action": "fill",
        "value": "standard_user",
        "expected": "field_populated"
    },
    # ... more intents
]
```

**Requirements**:
- Must be deterministic (no LLM calls)
- Validate input format
- Handle missing regions gracefully
- Preserve original intent strings

---

### 4.2 POMBuilder Agent

**File**: `backend/agents/pom_builder.py`

**Signature**:
```python
@traced("pom_builder")
async def run(state: RunState) -> RunState:
    """Discover selectors using multi-strategy probing."""
```

**Process**:
1. Get URL from `state.context["url"]`
2. Navigate browser to URL
3. For each intent in `state.context["intents"]`:
   - Call `discover_selector(browser, intent)`
   - Try strategies in order: label → placeholder → role_name → ...
   - First match wins
   - Attach selector + confidence + strategy metadata

**Output** (to `state.context["plan"]`):
```python
[
    {
        **intent,  # Original intent fields
        "selector": "#username",
        "confidence": 0.88,
        "meta": {
            "strategy": "placeholder",
            "discovered_at": "2025-10-30T12:00:00Z"
        }
    },
    # ... more plan items
]
```

**Requirements**:
- Must try all strategies before failing
- Must attach confidence scores
- Must preserve original intent data
- Navigate to URL before discovery

---

### 4.3 Generator Agent

**File**: `backend/agents/generator.py`

**Signature**:
```python
@traced("generator")
async def run(state: RunState) -> RunState:
    """Generate Playwright test files from verified plan."""
```

**Template** (`backend/templates/test_template.py.j2`):
```python
import asyncio
from playwright.async_api import async_playwright

async def test_{{ test_name }}():
    """
    {{ test_description }}

    Generated by PACTS
    Discovery strategies used: {{ strategies_used }}
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto("{{ url }}")

        {% for step in steps %}
        # Step {{ loop.index }}: {{ step.action }} {{ step.element }}
        # Selector: {{ step.selector }} ({{ step.meta.strategy }}, confidence: {{ step.confidence }})
        {% if step.action == "fill" %}
        await page.locator("{{ step.selector }}").fill("{{ step.value }}")
        {% elif step.action == "click" %}
        await page.locator("{{ step.selector }}").click()
        {% endif %}
        {% endfor %}

        await browser.close()
```

**Output**:
- File: `generated_tests/test_<req_id>.py`
- Includes all discovered selectors
- Comments show strategies used
- Runnable with `pytest`

**Requirements**:
- Use Jinja2 for templating
- Include discovery metadata as comments
- Generate valid, runnable Playwright code
- Handle all 9 action types

---

### 4.4 Executor Agent

**File**: `backend/agents/executor.py`

**Signature**:
```python
@traced("executor")
async def run(state: RunState) -> RunState:
    """Execute actions with five-point gate validation."""
```

**Execution Loop**:
```python
for step in state.plan:
    if state.step_idx >= len(state.plan):
        break  # All steps done

    current_step = state.plan[state.step_idx]
    selector = current_step["selector"]
    action = current_step["action"]
    value = current_step.get("value")

    # Validate with five-point gate
    element = await browser.query(selector)
    if not element:
        state.failure = Failure.timeout
        return state

    gates = await five_point_gate(browser, selector, element)
    if not all(gates.values()):
        state.failure = gate_failure_type(gates)
        return state

    # Execute action
    success = await perform_action(browser, action, selector, value)
    if not success:
        state.failure = Failure.timeout
        return state

    # Record success
    state.step_idx += 1
    state.context["executed_steps"].append({
        "step_idx": state.step_idx - 1,
        "selector": selector,
        "action": action,
        "value": value,
        "heal_round": state.heal_round
    })

# All steps completed
if state.step_idx >= len(state.plan):
    state.verdict = "pass"

return state
```

**Supported Actions** (9 types):
1. `click` - Click element
2. `fill` - Fill input/textarea
3. `type` - Type with delay (human-like)
4. `press` - Press keyboard keys
5. `select` - Select dropdown option
6. `check` - Check checkbox
7. `uncheck` - Uncheck checkbox
8. `hover` - Hover over element
9. `focus` - Focus on element

**Requirements**:
- Must validate EVERY action with five-point gate
- Must never raise exceptions (return Failure enum)
- Must track `executed_steps` for Generator
- Must update `step_idx` on success
- Must set appropriate `Failure` enum on errors

---

### 4.5 OracleHealer Agent

**File**: `backend/agents/oracle_healer.py`

**Signature**:
```python
@traced("oracle_healer")
async def run(state: RunState) -> RunState:
    """Autonomous healing for failed selectors/actions."""
```

**Healing Strategies** (Priority Order):

**v1 (Phase 1)**:
```python
# Simple reprobe
state.heal_round += 1
state.failure = Failure.none
# Retry will use same selectors
return state
```

**v2 (Phase 2)**:
```python
async def heal(state: RunState) -> RunState:
    state.heal_round += 1

    failure_type = state.failure
    selector = state.last_selector

    if failure_type == Failure.not_visible:
        # Reveal strategy
        await reveal_element(browser, selector)
        # Scroll into view
        # Remove overlays
        # Wait for visibility

    elif failure_type == Failure.not_unique:
        # Reprobe strategy
        await reprobe_with_context(browser, intent)
        # Try scoped selectors
        # Add region context

    elif failure_type == Failure.unstable:
        # Stability wait strategy
        await wait_for_stability(browser, selector)
        # Wait for animations
        # Check DOM mutations

    elif failure_type == Failure.timeout:
        # Adaptive timeout strategy
        await retry_with_longer_timeout(browser, selector)

    state.failure = Failure.none
    return state
```

**Healing Limits**:
- Max 3 healing rounds (`state.heal_round < 3`)
- After 3 rounds → route to VerdictRCA with failure
- Each round increments `state.heal_round`

**Requirements**:
- Must track `heal_round` count
- Must reset `failure` to `Failure.none` after healing
- Must not exceed 3 healing attempts
- Must preserve execution history

---

### 4.6 VerdictRCA Agent

**File**: `backend/agents/verdict_rca.py`

**Signature**:
```python
@traced("verdict_rca")
async def run(state: RunState) -> RunState:
    """Compute verdict and root cause analysis."""
```

**Verdict Classification**:
```python
if state.step_idx >= len(state.plan) and state.failure == Failure.none:
    verdict = "pass"
    rca = "All steps executed successfully"

elif state.failure != Failure.none:
    verdict = "fail"
    rca = classify_failure(state)

else:
    verdict = "partial"
    rca = f"Completed {state.step_idx}/{len(state.plan)} steps"
```

**RCA Classification Taxonomy**:

| Class | Trigger | Description |
|-------|---------|-------------|
| `selector_drift` | not_unique or timeout after reprobe | Selector no longer unique/valid |
| `timing_instability` | unstable or intermittent failures | Element animating or loading |
| `visibility_issue` | not_visible despite reveal | Element hidden by CSS/overlay |
| `enablement_issue` | disabled | Element disabled by app state |
| `assertion_mismatch` | Expected outcome not met | Wrong page/content |
| `data_issue` | Fill value rejected | Invalid input data |
| `env_fault` | Network timeout, page crash | Environment/infrastructure issue |

**Output** (to `state.context["rca"]`):
```python
{
    "class": "timing_instability",
    "confidence": 0.75,
    "evidence": [
        "Element unstable (bbox changed 3 times)",
        "Healed after 2 rounds with stability wait"
    ],
    "recommendation": "Add explicit wait for animation completion"
}
```

**Requirements**:
- Must classify ALL outcomes (pass, fail, partial)
- Must provide actionable RCA for failures
- Must calculate metrics (execution time, heal rounds, etc.)
- Must persist verdict to database

---

## 5. Discovery Strategies

**File**: `backend/runtime/discovery.py`

### 5.1 Strategy Architecture

```python
STRATEGIES = [
    "label",           # Priority 1: 0.92 confidence
    "placeholder",     # Priority 2: 0.88 confidence
    "role_name",       # Priority 3: 0.95 confidence
    "relational_css",  # Priority 4: 0.85 confidence
    "shadow_pierce",   # Priority 5: 0.80 confidence
    "fallback_css",    # Priority 6: 0.70 confidence
]

async def discover_selector(browser, intent):
    """Try strategies in order until one succeeds."""
    for strategy_name in STRATEGIES:
        result = await STRATEGY_FUNCS[strategy_name](browser, intent)
        if result:
            return result
    return None  # No strategy succeeded
```

### 5.2 Label Strategy (0.92 confidence)

**Purpose**: Find inputs associated with `<label>` elements

**Implementation**:
```python
async def _try_label(browser, intent):
    name = intent.get("element")  # e.g., "Username"
    pattern = re.compile(re.escape(name), re.I)

    # Find label with matching text
    found = await browser.find_by_label(pattern)
    if not found:
        return None

    selector, element = found
    return {
        "selector": selector,
        "score": 0.92,
        "meta": {"strategy": "label", "name": name}
    }
```

**Browser Helper** (`backend/runtime/browser_client.py`):
```python
async def find_by_label(self, text_pattern):
    """Resolve <label for="id"> → input#id mapping."""
    # Find label element
    label = self.page.get_by_text(text_pattern).locator('xpath=ancestor-or-self::label[1]')

    # Get 'for' attribute
    for_attr = await label.get_attribute('for')
    if for_attr:
        return f"#{for_attr}", await self.page.query_selector(f"#{for_attr}")

    # Fallback: input inside label
    inner = label.locator('input, textarea')
    if await inner.count() > 0:
        handle = await inner.first.element_handle()
        # Synthesize selector (prefer id > name)
        id_val = await handle.get_attribute('id')
        if id_val:
            return f"#{id_val}", handle
        name_val = await handle.get_attribute('name')
        if name_val:
            return f'[name="{name_val}"]', handle

    return None
```

**Coverage**: 60-70% of form inputs

---

### 5.3 Placeholder Strategy (0.88 confidence)

**Purpose**: Find inputs by placeholder attribute

**Implementation**:
```python
async def _try_placeholder(browser, intent):
    name = intent.get("element")
    pattern = re.compile(re.escape(name), re.I)

    found = await browser.find_by_placeholder(pattern)
    if not found:
        return None

    selector, element = found
    return {
        "selector": selector,
        "score": 0.88,
        "meta": {"strategy": "placeholder", "name": name}
    }
```

**Browser Helper**:
```python
async def find_by_placeholder(self, text_pattern):
    """Find inputs with matching placeholder."""
    loc = self.page.locator('[placeholder]')
    count = await loc.count()

    for i in range(min(count, 50)):  # Scan first 50
        item = loc.nth(i)
        ph = await item.get_attribute('placeholder')

        if text_pattern.search(ph):  # Regex match
            handle = await item.element_handle()
            # Synthesize stable selector
            id_val = await handle.get_attribute('id')
            if id_val:
                return f"#{id_val}", handle
            name_val = await handle.get_attribute('name')
            if name_val:
                return f'[name="{name_val}"]', handle
            return f'[placeholder*="{ph}"]', handle

    return None
```

**Coverage**: 50-60% of modern UIs

---

### 5.4 role_name Strategy (0.95 confidence)

**Purpose**: Find interactive elements by ARIA role + accessible name

**ROLE_HINTS** (keyword → role mapping):
```python
ROLE_HINTS = {
    "login": "button",
    "submit": "button",
    "sign in": "button",
    "continue": "button",
    "next": "button",
    "ok": "button",
    "search": "button",
    "menu": "button",
    "tab": "tab",
    "link": "link",
}
```

**Implementation**:
```python
async def _try_role_name(browser, intent):
    name = intent.get("element")
    action = intent.get("action", "").lower()

    # Determine role
    role = None
    if action == "click":
        role = "button"  # Default for click actions

    # Check ROLE_HINTS
    for keyword, hint_role in ROLE_HINTS.items():
        if keyword in name.lower():
            role = hint_role
            break

    # Try candidate roles
    candidates = [role] if role else ["button", "link", "tab"]
    pattern = re.compile(re.escape(name), re.I)

    for r in candidates:
        found = await browser.find_by_role(r, pattern)
        if found:
            selector, element = found
            return {
                "selector": selector,
                "score": 0.95,  # Highest confidence
                "meta": {"strategy": "role_name", "role": r, "name": name}
            }

    return None
```

**Browser Helper**:
```python
async def find_by_role(self, role, name_pattern):
    """Use Playwright's get_by_role."""
    locator = self.page.get_by_role(role, name=name_pattern)

    if await locator.count() == 0:
        return None

    handle = await locator.first.element_handle()

    # Synthesize stable selector (priority: id > name > aria-label)
    id_val = await handle.get_attribute('id')
    if id_val:
        return f"#{id_val}", handle

    name_val = await handle.get_attribute('name')
    if name_val:
        return f'[name="{name_val}"]', handle

    aria_label = await handle.get_attribute('aria-label')
    if aria_label:
        return f'[role="{role}"][aria-label*="{aria_label}"]', handle

    # Fallback: role selector with name pattern
    return f'role={role}[name~="{name_pattern.pattern}"]', handle
```

**Coverage**: 30-40% (buttons, links, tabs)

**Why Highest Confidence?**
- ARIA roles are semantic (defined by W3C)
- Used by screen readers → reliable signal
- Less affected by CSS changes

---

### 5.5 Combined Strategy Coverage

| Strategy | Confidence | Elements Covered | Overlap |
|----------|-----------|------------------|---------|
| label | 0.92 | Form inputs with labels | ~50% |
| placeholder | 0.88 | Modern form inputs | ~40% |
| role_name | 0.95 | Buttons, links, tabs | ~20% |
| **Combined** | - | **90%+ of common elements** | Minimal |

**Strategy Selection Logic**:
- Try high-confidence strategies first (but role_name is 3rd due to specificity)
- First match wins (no ambiguity)
- Attach metadata for debugging

---

## 6. Five-Point Actionability Gate

**File**: `backend/runtime/policies.py`

### 6.1 Purpose

Validate that an element is **safe and ready** for interaction BEFORE performing any action.

### 6.2 The Five Points

```python
async def five_point_gate(browser, selector: str, element) -> Dict[str, bool]:
    """
    Validate element against five actionability criteria.

    All five must pass for element to be actionable.
    """
    count = await browser.locator_count(selector)

    gates = {
        "unique": count == 1,                          # 1. Uniqueness
        "visible": await browser.visible(element),     # 2. Visibility
        "enabled": await browser.enabled(element),     # 3. Enablement
        "stable_bbox": await browser.bbox_stable(element),  # 4. Stability
        "scoped": True,  # 5. Scoping (future: frame/shadow DOM)
    }

    return gates
```

### 6.3 Gate Specifications

#### Gate 1: Unique (No Ambiguity)
**Check**: Selector matches exactly 1 element
**Failure**: `Failure.not_unique`

```python
"unique": await browser.locator_count(selector) == 1
```

**Why Critical?**
- Prevents accidental interaction with wrong element
- Ensures deterministic behavior

---

#### Gate 2: Visible (User Can See It)
**Check**: Element is visible on page
**Failure**: `Failure.not_visible`

```python
"visible": await element.is_visible()
```

**Why Critical?**
- User can't interact with hidden elements
- Prevents false positives (element exists but not shown)

---

#### Gate 3: Enabled (Not Disabled)
**Check**: Element is not disabled
**Failure**: `Failure.disabled`

```python
"enabled": await element.is_enabled()
```

**Why Critical?**
- Disabled elements reject interactions
- Indicates app state not ready

---

#### Gate 4: Stable (Not Animating)
**Check**: Bounding box stable across 3 samples
**Failure**: `Failure.unstable`

```python
async def bbox_stable(element, samples=3, delay_ms=120, tolerance=2.0):
    """Check if element's position/size is stable."""
    boxes = []
    for _ in range(samples):
        box = await element.bounding_box()
        if not box:
            return False
        boxes.append(box)
        await self.page.wait_for_timeout(delay_ms)

    # Check if all samples match within tolerance
    for i in range(1, len(boxes)):
        for key in ["x", "y", "width", "height"]:
            if abs(boxes[i][key] - boxes[0][key]) > tolerance:
                return False

    return True
```

**Why Critical?**
- Prevents clicking during animations
- Avoids race conditions with dynamic content

---

#### Gate 5: Scoped (Correct Context)
**Check**: Element in correct frame/shadow DOM
**Failure**: (Future implementation)

```python
"scoped": True  # Phase 1: Always pass (single frame)
                # Phase 2: Validate frame/shadow context
```

**Why Critical?**
- Iframes require special handling
- Shadow DOM needs piercing

---

### 6.4 Gate Failure Handling

```python
gates = await five_point_gate(browser, selector, element)

if not gates["unique"]:
    state.failure = Failure.not_unique
    return state
elif not gates["visible"]:
    state.failure = Failure.not_visible
    return state
elif not gates["enabled"]:
    state.failure = Failure.disabled
    return state
elif not gates["stable_bbox"]:
    state.failure = Failure.unstable
    return state
# scoped always True in Phase 1

# All gates passed - safe to interact
await perform_action(...)
```

---

## 7. LangGraph Orchestration

**File**: `backend/graph/build_graph.py`

### 7.1 State Definition

**File**: `backend/graph/state.py`

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Dict, Any, Optional, List

class Failure(str, Enum):
    """Failure types for routing decisions."""
    none = "none"
    not_unique = "not_unique"
    not_visible = "not_visible"
    disabled = "disabled"
    unstable = "unstable"
    timeout = "timeout"

class RunState(BaseModel):
    """
    Shared state passed between agents.

    LangGraph manages state persistence and updates.
    """
    req_id: str                                    # Unique request ID
    step_idx: int = 0                             # Current step index
    heal_round: int = 0                           # Healing attempt counter
    context: Dict[str, Any] = Field(default_factory=dict)  # Flexible context
    failure: Failure = Failure.none               # Current failure state
    last_selector: Optional[str] = None           # For healing
    verdict: Optional[str] = None                 # Final verdict

    @property
    def plan(self) -> List[Dict[str, Any]]:
        """Helper to access plan from context."""
        return self.context.get("plan", [])
```

### 7.2 Graph Construction

```python
from langgraph.graph import StateGraph, END

def build_graph():
    """
    Build the complete PACTS agent graph.

    Flow:
    1. Planner → Parse requirements
    2. POMBuilder → Discover selectors
    3. Generator → Generate test code
    4. Executor → Run actions
    5. OracleHealer → Heal failures (conditional)
    6. VerdictRCA → Compute verdict
    """
    g = StateGraph(RunState)

    # Import agents
    from backend.agents import planner, pom_builder, generator, executor

    # Add agent nodes
    g.add_node("planner", planner.run)
    g.add_node("pom_builder", pom_builder.run)
    g.add_node("generator", generator.run)
    g.add_node("executor", executor.run)
    g.add_node("oracle_healer", oracle_healer_stub)  # Stub in Phase 1
    g.add_node("verdict_rca", verdict_rca_stub)      # Stub in Phase 1

    # Define routing
    g.set_entry_point("planner")
    g.add_edge("planner", "pom_builder")
    g.add_edge("pom_builder", "generator")
    g.add_edge("generator", "executor")

    # Conditional routing from executor
    g.add_conditional_edges(
        "executor",
        should_heal,  # Routing function
        {
            "executor": "executor",        # Loop: next step
            "oracle_healer": "oracle_healer",  # Heal failure
            "verdict_rca": "verdict_rca",      # Finish
        }
    )

    # After healing, retry executor
    g.add_edge("oracle_healer", "executor")

    # After verdict, done
    g.add_edge("verdict_rca", END)

    return g.compile()
```

### 7.3 Routing Logic

```python
def should_heal(state: RunState) -> str:
    """
    Decide next node based on state.

    Returns:
        "executor" - Continue to next step
        "oracle_healer" - Heal failure
        "verdict_rca" - Compute final verdict
    """
    # All steps completed successfully
    if state.step_idx >= len(state.plan) and state.failure == Failure.none:
        return "verdict_rca"

    # Failure detected
    if state.failure != Failure.none:
        # Try healing (max 3 rounds)
        if state.heal_round < 3:
            return "oracle_healer"
        else:
            # Max healing attempts reached
            return "verdict_rca"

    # More steps to execute
    return "executor"
```

### 7.4 Graph Execution

```python
async def run_pacts(req_id: str, url: str, raw_steps: List[str]):
    """Execute complete PACTS pipeline."""
    # Initialize state
    state = RunState(
        req_id=req_id,
        context={
            "url": url,
            "raw_steps": raw_steps
        }
    )

    # Build and run graph
    app = build_graph()
    result = await app.ainvoke(state)

    # result is final RunState with verdict
    return result
```

---

## 8. Data Contracts

### 8.1 Input Format (Requirements)

**Excel Format**:
```
| Element@Region      | Action | Value          | Expected Outcome    |
|---------------------|--------|----------------|---------------------|
| Username@LoginForm  | fill   | standard_user  | field_populated     |
| Password@LoginForm  | fill   | secret_sauce   | field_populated     |
| Login@LoginForm     | click  |                | navigates_to:Products |
```

**JSON Format**:
```json
{
  "req_id": "REQ-LOGIN-001",
  "url": "https://www.saucedemo.com",
  "steps": [
    {
      "element": "Username",
      "region": "LoginForm",
      "action": "fill",
      "value": "standard_user",
      "expected": "field_populated"
    },
    {
      "element": "Password",
      "region": "LoginForm",
      "action": "fill",
      "value": "secret_sauce",
      "expected": "field_populated"
    },
    {
      "element": "Login",
      "region": "LoginForm",
      "action": "click",
      "expected": "navigates_to:Products"
    }
  ]
}
```

### 8.2 Internal State (RunState.context)

**After Planner**:
```python
{
    "url": "https://www.saucedemo.com",
    "raw_steps": [...],
    "intents": [
        {
            "intent": "Username@LoginForm",
            "element": "Username",
            "region": "LoginForm",
            "action": "fill",
            "value": "standard_user"
        },
        # ...
    ]
}
```

**After POMBuilder**:
```python
{
    # ... previous context
    "plan": [
        {
            "intent": "Username@LoginForm",
            "element": "Username",
            "region": "LoginForm",
            "action": "fill",
            "value": "standard_user",
            "selector": "#user-name",
            "confidence": 0.88,
            "meta": {"strategy": "placeholder"}
        },
        # ...
    ]
}
```

**After Executor**:
```python
{
    # ... previous context
    "executed_steps": [
        {
            "step_idx": 0,
            "selector": "#user-name",
            "action": "fill",
            "value": "standard_user",
            "heal_round": 0,
            "timestamp": "2025-10-30T12:00:00Z"
        },
        # ...
    ]
}
```

**After VerdictRCA**:
```python
{
    # ... previous context
    "rca": {
        "class": "success",
        "confidence": 1.0,
        "message": "All steps executed successfully",
        "metrics": {
            "total_steps": 3,
            "executed_steps": 3,
            "heal_rounds": 0,
            "execution_time_ms": 5420
        }
    }
}
```

### 8.3 Output Format (Verdict Report)

**JSON Output** (`verdict_<req_id>.json`):
```json
{
  "req_id": "REQ-LOGIN-001",
  "verdict": "pass",
  "timestamp": "2025-10-30T12:00:05Z",
  "summary": {
    "total_steps": 3,
    "executed_steps": 3,
    "failed_steps": 0,
    "heal_rounds": 0
  },
  "rca": {
    "class": "success",
    "confidence": 1.0,
    "message": "All steps executed successfully"
  },
  "steps": [
    {
      "step_idx": 0,
      "element": "Username",
      "action": "fill",
      "selector": "#user-name",
      "strategy": "placeholder",
      "confidence": 0.88,
      "status": "success",
      "heal_round": 0
    },
    // ...
  ],
  "artifacts": {
    "test_file": "generated_tests/test_REQ-LOGIN-001.py",
    "test_hash": "sha256:abc123..."
  }
}
```

---

## 9. Memory & Persistence

### 9.1 Postgres Schema

**Tables**:

```sql
-- Runs table: One row per PACTS execution
CREATE TABLE runs (
    req_id VARCHAR(100) PRIMARY KEY,
    url TEXT NOT NULL,
    verdict VARCHAR(20),  -- 'pass', 'fail', 'partial'
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    heal_rounds INTEGER DEFAULT 0,
    rca_class VARCHAR(50),
    rca_message TEXT,
    CONSTRAINT valid_verdict CHECK (verdict IN ('pass', 'fail', 'partial'))
);

-- Steps table: One row per step executed
CREATE TABLE run_steps (
    id SERIAL PRIMARY KEY,
    req_id VARCHAR(100) REFERENCES runs(req_id),
    step_idx INTEGER,
    element VARCHAR(200),
    action VARCHAR(50),
    selector TEXT,
    strategy VARCHAR(50),
    confidence DECIMAL(3,2),
    status VARCHAR(20),  -- 'success', 'failed'
    heal_round INTEGER DEFAULT 0,
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT NOW()
);

-- Artifacts table: Generated test files
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    req_id VARCHAR(100) REFERENCES runs(req_id),
    artifact_type VARCHAR(50),  -- 'test_file', 'verdict_report'
    file_path TEXT,
    file_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Metrics table: Performance metrics
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    req_id VARCHAR(100) REFERENCES runs(req_id),
    metric_name VARCHAR(100),
    metric_value DECIMAL(10,2),
    recorded_at TIMESTAMP DEFAULT NOW()
);
```

### 9.2 Redis Caching

**Keys**:

```python
# Selector cache (POM cache)
# Key: f"pom:{url}:{element}"
# Value: {"selector": "#id", "confidence": 0.95, "ttl": 3600}
pom:https://saucedemo.com:Username → {"selector": "#user-name", ...}

# Graph checkpoints (LangGraph state)
# Key: f"checkpoint:{req_id}"
# Value: Serialized RunState
checkpoint:REQ-001 → {pickled RunState}

# Healing counters
# Key: f"heal:{req_id}:{selector}"
# Value: Integer counter
heal:REQ-001:#button → 2

# Rate limiting
# Key: f"rate:{client_id}"
# Value: Request count (with TTL)
rate:client_123 → 15 (expires in 60s)
```

**TTL Values**:
- POM cache: 1 hour (selectors may change)
- Checkpoints: 24 hours (for replay)
- Heal counters: 1 hour (per session)
- Rate limits: 60 seconds (sliding window)

---

## 10. API Specifications

**File**: `backend/api/main.py`

### 10.1 REST Endpoints

#### POST /run
**Purpose**: Start a PACTS execution

**Request**:
```json
{
  "req_id": "REQ-LOGIN-001",
  "url": "https://www.saucedemo.com",
  "steps": [
    "Username@LoginForm | fill | standard_user",
    "Password@LoginForm | fill | secret_sauce",
    "Login@LoginForm | click"
  ]
}
```

**Response** (202 Accepted):
```json
{
  "req_id": "REQ-LOGIN-001",
  "status": "running",
  "message": "PACTS execution started"
}
```

---

#### GET /runs/{req_id}
**Purpose**: Get run status and verdict

**Response**:
```json
{
  "req_id": "REQ-LOGIN-001",
  "status": "completed",
  "verdict": "pass",
  "started_at": "2025-10-30T12:00:00Z",
  "finished_at": "2025-10-30T12:00:05Z",
  "summary": {
    "total_steps": 3,
    "executed_steps": 3,
    "heal_rounds": 0
  }
}
```

---

#### GET /runs/{req_id}/steps
**Purpose**: Get detailed step execution history

**Response**:
```json
{
  "req_id": "REQ-LOGIN-001",
  "steps": [
    {
      "step_idx": 0,
      "element": "Username",
      "action": "fill",
      "selector": "#user-name",
      "strategy": "placeholder",
      "confidence": 0.88,
      "status": "success",
      "heal_round": 0
    },
    // ...
  ]
}
```

---

#### GET /artifacts/{req_id}
**Purpose**: Get generated test file

**Response**:
```json
{
  "req_id": "REQ-LOGIN-001",
  "artifacts": [
    {
      "type": "test_file",
      "path": "generated_tests/test_REQ-LOGIN-001.py",
      "hash": "sha256:abc123...",
      "size_bytes": 1234
    },
    {
      "type": "verdict_report",
      "path": "verdicts/verdict_REQ-LOGIN-001.json",
      "hash": "sha256:def456...",
      "size_bytes": 567
    }
  ]
}
```

---

#### GET /health
**Purpose**: Service health check

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "postgres": "connected",
    "redis": "connected",
    "playwright": "ready"
  }
}
```

---

## 11. Testing Requirements

### 11.1 Unit Tests

**Coverage Target**: ≥80% code coverage

**Test Files**:
- `backend/tests/unit/test_planner.py` - Planner parsing logic
- `backend/tests/unit/test_discovery.py` - All discovery strategies
- `backend/tests/unit/test_executor.py` - Executor actions and gates
- `backend/tests/unit/test_policies.py` - Five-point gate validation
- `backend/tests/unit/test_oracle_healer.py` - Healing strategies
- `backend/tests/unit/test_verdict_rca.py` - Verdict classification

**Testing Approach**:
```python
# Use fake browsers (no Playwright needed)
class FakeBrowser:
    def __init__(self):
        self.page = FakePage()

    async def query(self, selector):
        return FakeElement()

# Fast tests (no actual browser launch)
@pytest.mark.asyncio
async def test_executor_click():
    browser = FakeBrowser()
    state = RunState(req_id="TEST", context={"plan": [...]})

    result = await executor.run(state)

    assert result.step_idx == 1
    assert result.failure == Failure.none
```

### 11.2 Integration Tests

**Test Files**:
- `backend/tests/integration/test_saucedemo.py` - Full SauceDemo login flow
- `backend/tests/integration/test_role_discovery.py` - Role strategy validation
- `backend/tests/integration/test_healing.py` - Healing scenarios

**Testing Approach**:
```python
# Use real Playwright browser
async def test_saucedemo_login():
    browser = BrowserClient()
    await browser.start(headless=True)

    state = RunState(
        req_id="INT-TEST-001",
        context={
            "url": "https://www.saucedemo.com",
            "raw_steps": [
                "Username | fill | standard_user",
                "Password | fill | secret_sauce",
                "Login | click"
            ]
        }
    )

    result = await run_pacts(state)

    assert result.verdict == "pass"
    assert len(result.context["executed_steps"]) == 3

    await browser.close()
```

### 11.3 Test Success Criteria

- All unit tests pass in <1 second
- All integration tests pass in <30 seconds
- SauceDemo login: 3/3 steps discovered and executed
- Code coverage ≥80%
- No flaky tests (100% pass rate on 10 runs)

---

## 12. Deployment Architecture

### 12.1 Container Structure

```
docker-compose.yml:
  services:
    pacts-api:
      build: ./backend
      ports: ["8000:8000"]
      depends_on: [postgres, redis]
      environment:
        - DATABASE_URL=postgresql://...
        - REDIS_URL=redis://...
        - LANGSMITH_API_KEY=...

    postgres:
      image: postgres:15
      volumes: ["pgdata:/var/lib/postgresql/data"]
      environment:
        - POSTGRES_DB=pacts
        - POSTGRES_USER=pacts
        - POSTGRES_PASSWORD=...

    redis:
      image: redis:7-alpine
      volumes: ["redisdata:/data"]

    playwright-browsers:
      build: ./playwright
      # Separate container for browser pool
```

### 12.2 Scaling Strategy

**Horizontal Scaling**:
- API pods: N replicas (stateless FastAPI)
- Worker pods: M replicas (PACTS execution)
- Redis: Shared state (cluster mode)
- Postgres: Primary + replicas

**Resource Allocation**:
```yaml
pacts-api:
  cpu: 1000m
  memory: 2Gi

pacts-worker:
  cpu: 2000m  # Browser automation is CPU-intensive
  memory: 4Gi  # Browsers need memory

postgres:
  cpu: 2000m
  memory: 8Gi

redis:
  cpu: 500m
  memory: 2Gi
```

### 12.3 Environment Configuration

**.env.example**:
```bash
# Database
DATABASE_URL=postgresql://pacts:password@postgres:5432/pacts
REDIS_URL=redis://redis:6379/0

# Playwright
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT=30000

# LangSmith
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=pacts-production

# API
API_KEY=your_secret_key
CORS_ORIGINS=http://localhost:3000,https://dashboard.pacts.io

# Healing
MAX_HEAL_ROUNDS=3
HEAL_TIMEOUT_MS=60000

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGS=true
```

---

## Appendix A: File Structure

Complete project structure:

```
pacts/
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── planner.py              # Requirement parser
│   │   ├── pom_builder.py          # Selector discovery
│   │   ├── generator.py            # Test code generation
│   │   ├── executor.py             # Action execution
│   │   ├── oracle_healer.py        # Autonomous healing
│   │   └── verdict_rca.py          # Verdict & RCA
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py                # RunState definition
│   │   └── build_graph.py          # LangGraph construction
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── browser_client.py       # Playwright wrapper
│   │   ├── browser_manager.py      # Singleton manager
│   │   ├── discovery.py            # Discovery strategies
│   │   └── policies.py             # Five-point gate
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── routes/
│   │   │   ├── runs.py
│   │   │   ├── artifacts.py
│   │   │   └── health.py
│   │   └── models/
│   │       ├── request.py
│   │       └── response.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py                 # CLI interface
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── postgres.py             # Postgres adapter
│   │   └── redis.py                # Redis adapter
│   ├── telemetry/
│   │   ├── __init__.py
│   │   └── tracing.py              # LangSmith integration
│   ├── templates/
│   │   └── test_template.py.j2     # Jinja2 test template
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_planner.py
│   │   │   ├── test_discovery.py
│   │   │   ├── test_executor.py
│   │   │   ├── test_policies.py
│   │   │   └── ...
│   │   └── integration/
│   │       ├── test_saucedemo.py
│   │       ├── test_role_discovery.py
│   │       └── ...
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── README.md
├── docs/
│   ├── PHASE-1-COMPLETE.md
│   ├── EXECUTOR-AGENT-DELIVERED.md
│   ├── ROLE-NAME-STRATEGY-DELIVERED.md
│   └── ...
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile
├── .env.example
├── README.md
└── PACTS-COMPLETE-SPECIFICATION.md  # This document
```

---

## Appendix B: Success Metrics

### Phase 1 Targets

| Metric | Target | Verification |
|--------|--------|--------------|
| Discovery Coverage | ≥90% | Test on 50 diverse websites |
| Execution Success Rate | ≥85% | SauceDemo + 10 other sites |
| Healing Success Rate | ≥60% | Inject failures, measure recovery |
| Test Generation Quality | 100% runnable | Generated tests pass with pytest |
| API Latency (p95) | <10s | For typical 5-step flow |
| Code Coverage | ≥80% | Unit + integration tests |

### Phase 2 Targets

| Metric | Target | Description |
|--------|--------|-------------|
| Discovery Coverage | ≥95% | Add shadow DOM, relational CSS |
| Healing Success Rate | ≥80% | Advanced reveal/reprobe strategies |
| Multi-Site Success | ≥90% | Test on 100 diverse sites |
| Flakiness Rate | <5% | Tests fail due to randomness |

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **Find-First Verification** | Discover and verify selectors BEFORE generating test code |
| **Five-Point Gate** | Validation: unique, visible, enabled, stable, scoped |
| **ROLE_HINTS** | Keyword → ARIA role mapping (e.g., "login" → "button") |
| **Healing Round** | Attempt to recover from failure (max 3) |
| **RCA** | Root Cause Analysis - classification of failure reason |
| **POM** | Page Object Model - cache of element selectors |
| **RunState** | Shared state passed between agents in LangGraph |
| **LangSmith** | Observability platform for tracing agent decisions |

---

## Document Version

**Version**: 1.0
**Last Updated**: 2025-10-30
**Status**: AUTHORITATIVE SPECIFICATION
**Audience**: AI Code Assistants (Claude Code, Copilot, Cursor)

---

## How to Use This Document

### For AI Code Assistants

1. **Read Sections 1-3** for system vision and architecture
2. **Implement Agents** following Section 4 specifications exactly
3. **Implement Discovery** using Section 5 strategy details
4. **Implement Five-Point Gate** per Section 6 specifications
5. **Wire LangGraph** following Section 7 orchestration
6. **Add Tests** meeting Section 11 requirements
7. **Deploy** using Section 12 architecture

### For Human Developers

This document is optimized for AI code generation. Humans should also read:
- `/docs/PHASE-1-COMPLETE.md` for implementation status
- `/docs/EXECUTOR-AGENT-DELIVERED.md` for executor details
- `/docs/ROLE-NAME-STRATEGY-DELIVERED.md` for discovery details

### For QA/Handoff

This specification defines:
- ✅ What PACTS should do (requirements)
- ✅ How it should work (architecture)
- ✅ How to verify it works (tests)
- ✅ How to deploy it (infrastructure)

---

**END OF SPECIFICATION**

This document is complete and sufficient for building PACTS from scratch.
