# PACTS Technical Specification v2.1

**Production-Ready Autonomous Context Testing System**

_Comprehensive specification including current state + future vision_

---

## Document Purpose

This document serves as the **authoritative technical specification** for PACTS v2.1 and beyond. It includes:

1. **Current Architecture (v2.1)** - What we've built and validated in production
2. **Memory & Persistence** - Database schema and caching strategy (to be implemented)
3. **Telemetry & Observability** - LangSmith integration and monitoring (to be implemented)
4. **Observability API** - REST endpoints for querying runs and metrics (to be implemented)
5. **Implementation Roadmap** - Priorities and timelines

**Target Readers**:
- Developers extending PACTS
- AI code assistants implementing features
- Stakeholders evaluating production readiness
- Enterprise architects assessing PACTS for adoption

**Version**: 2.1
**Status**: Current architecture ✅ Production Ready | Memory/Telemetry/Observability 🚧 Planned
**Last Updated**: 2025-11-02

---

## Table of Contents

1. [System Vision & Philosophy](#1-system-vision--philosophy)
2. [Architecture Overview (v2.1)](#2-architecture-overview-v21)
3. [Technology Stack](#3-technology-stack)
4. [Agent Specifications](#4-agent-specifications)
5. [Discovery Strategies](#5-discovery-strategies)
6. [Five-Point Actionability Gate](#6-five-point-actionability-gate)
7. [App-Specific Helpers (v2.1 NEW)](#7-app-specific-helpers-v21-new)
8. [LangGraph Orchestration](#8-langgraph-orchestration)
9. [Memory & Persistence (PLANNED)](#9-memory--persistence-planned)
10. [Telemetry Integration (PLANNED)](#10-telemetry-integration-planned)
11. [Observability API (PLANNED)](#11-observability-api-planned)
12. [Data Contracts](#12-data-contracts)
13. [Implementation Roadmap](#13-implementation-roadmap)

---

## 1. System Vision & Philosophy

### 1.1 Core Problem

Traditional test automation requires:
- Manual selector creation (brittle, time-consuming)
- Hard-coded element locators (break on UI changes)
- No autonomous healing (tests fail, require manual fixes)
- No learning from past runs (same failures repeat)
- No observability (debugging is log archaeology)

### 1.2 PACTS Solution

**Find-First Verification™**: Discover and verify selectors BEFORE executing tests

**Autonomous Healing**: Self-correct failures during execution (OracleHealer)

**Memory-Enhanced Learning**: Remember successful strategies, avoid failed ones

**Full Observability**: Every decision traced, queryable, and replayable

### 1.3 Design Principles

1. **Verification-First**: Discover selectors via real DOM queries (no hallucinations)
2. **Observable**: Every decision traced to LangSmith (replay capability)
3. **Autonomous**: Heals failures without human intervention (max 3 attempts)
4. **Learnable**: Memory system learns from successes and failures
5. **Production-Grade**: Built for enterprise reliability, not demos

### 1.4 Key Differentiators

| Feature | Traditional Tools | PACTS v2.1 | PACTS v3.0 (with Memory) |
|---------|------------------|------------|--------------------------|
| Selector Discovery | Manual | Autonomous (90%+) | Autonomous + Cached |
| Failure Handling | Test fails | Self-heals (3 attempts) | Self-heals (learned strategies) |
| Learning | None | None | Remembers patterns |
| Observability | Logs only | Screenshots | Full traces + queryable |
| SPA Support | Limited | ✅ Salesforce Lightning | ✅ SAP, Oracle, ServiceNow |
| Maintenance | High | Medium | Low (learns over time) |

---

## 2. Architecture Overview (v2.1)

### 2.1 Six-Agent Pipeline

```
┌──────────┐
│ Planner  │  Parse requirements → normalized steps
└────┬─────┘
     │
     ▼
┌────────────┐
│ POMBuilder │  Discover selectors (Find-First) + page load wait
└─────┬──────┘
      │
      ▼
┌───────────┐
│ Generator │  Generate test.py with verified selectors
└─────┬─────┘
      │
      ▼
┌──────────┐
│ Executor │  Execute actions + five-point gate + app helpers
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

### 2.2 v2.1 Key Additions

**NEW in v2.1**:
- **App-Specific Helpers**: Salesforce Lightning support (`backend/runtime/salesforce_helpers.py`)
- **Multi-Strategy Combobox**: Type-ahead, aria-controls, keyboard navigation
- **SPA Page Load Wait**: Prevents premature discovery on async SPAs
- **Session Reuse**: Skip 2FA login (73.7h/year saved per developer)
- **Parent Clickability Detection**: Traverse to clickable containers

**Production Validation**:
- ✅ 100% success rate (6/6 sites)
- ✅ 0 heal rounds average
- ✅ Salesforce Lightning (10/10 steps, complex enterprise SPA)

### 2.3 Agent Responsibilities

| Agent | Input | Output | Purpose | Current Status |
|-------|-------|--------|---------|----------------|
| **Planner** | Requirements text | Normalized steps | Parse & validate | ✅ v2 Authoritative |
| **POMBuilder** | Steps | Verified selectors | Discovery + validation | ✅ + Page wait |
| **Generator** | Verified plan | test_*.py files | Generate runnable tests | ✅ Production |
| **Executor** | Test plan | Execution results | Run actions + gate | ✅ + App helpers |
| **OracleHealer** | Failures | Healed selectors | Autonomous recovery | ✅ v1 (3 retries) |
| **VerdictRCA** | All results | Verdict + RCA | Classify outcomes | ✅ Basic verdict |

---

## 3. Technology Stack

### 3.1 Current Stack (v2.1)

| Component | Version | Purpose | Status |
|-----------|---------|---------|--------|
| Python | 3.11+ | Runtime | ✅ Production |
| LangGraph | 1.0+ | Agent orchestration | ✅ Production |
| Playwright | Latest | Browser automation | ✅ Production |
| Pydantic | 2.6+ | Data validation | ✅ Production |
| Anthropic Claude | Latest | LLM (Planner, Healer) | ✅ Production |

### 3.2 Planned Stack (v3.0)

| Component | Version | Purpose | Status |
|-----------|---------|---------|--------|
| FastAPI | Latest | REST API | 🚧 Planned |
| Postgres | 15+ | Persistent storage | 🚧 Planned |
| Redis | 7+ | Caching & state | 🚧 Planned |
| LangSmith | Latest | Observability | 🚧 Planned |
| Alembic | Latest | DB migrations | 🚧 Planned |

### 3.3 Why These Choices?

**LangGraph**: Deterministic state machine with checkpointing
**Playwright**: Direct browser control (no hallucinated selectors)
**Postgres**: Persistent memory (runs, selectors, RCA)
**Redis**: Fast selector cache + healing counters
**LangSmith**: Distributed tracing + replay capability

---

## 4. Agent Specifications

### 4.1 Planner (v2 Authoritative)

**File**: `backend/agents/planner.py`

**Purpose**: Parse natural language requirements → normalized execution steps

**Current Implementation** (v2.1):
```python
async def run(self, state: RunState) -> RunState:
    """Parse requirements and create execution plan."""

    # Parse steps from requirement file
    steps = self._parse_requirements(state.context["raw_steps"])

    # Normalize field names (handle LLM variations)
    normalized = [normalize_step_fields(s) for s in steps]

    # Add region hints for dialog scoping
    enriched = self._add_region_hints(normalized)

    # Store in execution plan
    state.context["plan"] = enriched

    return state
```

**Key Features**:
- Handles multiple field name variations (element/target/intent)
- Dialog scoping hints (within='App Launcher')
- Data binding for parameterized tests
- Assertion derivation from expected outcomes

**Future Enhancements** (v3.0):
- Memory-based intent caching (remember common patterns)
- Confidence scoring per step
- Telemetry: Emit parsing duration to LangSmith

---

### 4.2 POMBuilder (Discovery)

**File**: `backend/agents/pom_builder.py`

**Purpose**: Discover and verify selectors using multi-strategy probing

**Current Implementation** (v2.1):
```python
async def run(self, state: RunState) -> RunState:
    """Discover selectors for all steps."""

    browser = state.context["browser"]
    plan = state.context["plan"]

    for step in plan:
        # CRITICAL: Wait for SPA page load (v2.1)
        await self._wait_for_page_load(browser)

        # Try discovery strategies in order
        result = (
            await self._try_label(browser, step) or
            await self._try_placeholder(browser, step) or
            await self._try_role_name(browser, step)
        )

        if result:
            step["selector"] = result["selector"]
            step["confidence"] = result["score"]
            step["strategy"] = result["meta"]["strategy"]
        else:
            state.failure = Failure.discovery
            break

    return state
```

**Discovery Strategies**:

| Strategy | Confidence | Coverage | When to Use |
|----------|-----------|----------|-------------|
| `label` | 0.92 | 60-70% | Form inputs with `<label>` |
| `placeholder` | 0.88 | 50-60% | Modern inputs with placeholder text |
| `role_name` | 0.95 | 30-40% | Buttons, links, tabs (ARIA roles) |

**v2.1 Enhancement**: Page load wait
```python
async def _wait_for_page_load(self, browser):
    """Wait for SPA to stabilize before discovery."""
    try:
        await browser.page.wait_for_load_state("domcontentloaded", timeout=3000)
        await browser.page.wait_for_timeout(1000)  # Settle time
    except Exception:
        pass  # Non-critical
```

**Future Enhancements** (v3.0):
- **Selector cache**: Check Redis for previously successful selectors
- **Smart retries**: If cache miss, try all strategies + fallbacks
- **Confidence boost**: Increase confidence if selector cached + recently used
- **Telemetry**: Emit discovery timing per strategy to LangSmith

**Memory Integration** (v3.0):
```python
async def _discover_with_memory(self, browser, step):
    """Try cached selector first, fallback to discovery."""

    element_name = step["element"]
    url = browser.page.url
    cache_key = f"pom:{url}:{element_name}"

    # Check Redis cache
    cached = await redis.get(cache_key)
    if cached:
        selector = cached["selector"]
        if await self._validate_selector(browser, selector):
            logger.info(f"[POM] ✅ Cache HIT: {element_name}")
            return {
                "selector": selector,
                "score": cached["confidence"] + 0.05,  # Boost for cache hit
                "meta": {"strategy": "cached", "original": cached["strategy"]}
            }

    # Cache miss - run full discovery
    result = await self._full_discovery(browser, step)

    if result:
        # Store in cache for future runs
        await redis.setex(
            cache_key,
            3600,  # 1 hour TTL
            json.dumps({
                "selector": result["selector"],
                "confidence": result["score"],
                "strategy": result["meta"]["strategy"]
            })
        )

    return result
```

---

### 4.3 Executor

**File**: `backend/agents/executor.py`

**Purpose**: Execute actions with five-point gate validation + app-specific helpers

**Current Implementation** (v2.1):
```python
async def run(self, state: RunState) -> RunState:
    """Execute all planned steps."""

    browser = state.context["browser"]
    plan = state.context["plan"]

    for idx, step in enumerate(plan):
        selector = step["selector"]
        action = step["action"]
        value = step.get("value")

        # Get locator
        locator = browser.page.locator(selector)

        # Five-point gate validation
        if not await self._validate_gate(locator):
            state.failure = Failure.gate
            state.step_idx = idx
            break

        # Check if app-specific helper needed
        if self._is_special_selector(selector):
            success = await self._handle_special(browser, selector, value)
            if not success:
                state.failure = Failure.timeout
                state.step_idx = idx
                break
            continue

        # Standard action execution
        try:
            if action == "click":
                await locator.click(timeout=5000)
            elif action == "fill":
                await locator.fill(value, timeout=5000)
            # ... other actions

            state.step_idx = idx + 1

        except Exception as e:
            state.failure = Failure.timeout
            state.step_idx = idx
            break

    return state
```

**v2.1 App-Specific Helpers**:
```python
async def _handle_special(self, browser, selector, value):
    """Route to app-specific helpers."""

    # Salesforce Lightning combobox
    if selector.startswith("role=combobox"):
        from ..runtime import salesforce_helpers as sf
        locator = browser.page.locator(selector)
        return await sf.handle_lightning_combobox(browser, locator, value)

    # Salesforce App Launcher search
    if sf.is_launcher_search(selector):
        target = sf.extract_launcher_target(selector)
        return await sf.handle_launcher_search(browser, target)

    return False
```

**Future Enhancements** (v3.0):
- **Telemetry**: Emit action duration + success/failure to LangSmith
- **Memory-based timeouts**: Adjust timeouts based on past execution times
- **Smart retries**: If action fails, check healing history before routing to healer

---

### 4.4 OracleHealer

**File**: `backend/agents/oracle_healer.py`

**Purpose**: Autonomous failure recovery (max 3 attempts)

**Current Implementation** (v1 stub):
```python
async def run(self, state: RunState) -> RunState:
    """Attempt to heal selector failure."""

    # Increment heal round
    state.heal_round += 1

    if state.heal_round > 3:
        # Max retries exceeded
        return state

    # Simple reprobe strategy
    failed_step = state.context["plan"][state.step_idx]

    # Re-run discovery for failed step
    pom_builder = POMBuilder()
    await pom_builder._discover_single_step(state, failed_step)

    return state
```

**Future Enhancements** (v2.0 - PRIORITY):
- **Reveal strategies**: Scroll into view, handle overlays, z-index issues
- **Reprobe alternates**: Try backup discovery strategies
- **Stability waits**: Dynamic wait times based on element behavior
- **Adaptive timeouts**: Increase timeout if first attempt was close

**Memory Integration** (v3.0):
```python
async def _heal_with_memory(self, state):
    """Use healing history to inform strategy."""

    failed_step = state.context["plan"][state.step_idx]
    element_name = failed_step["element"]
    selector = failed_step["selector"]

    # Check healing history
    heal_key = f"heal_history:{element_name}"
    history = await redis.lrange(heal_key, 0, 10)

    if history:
        # Analyze past successful heals
        strategies = [json.loads(h) for h in history]
        most_successful = max(strategies, key=lambda s: s["success_rate"])

        logger.info(f"[HEALER] 📚 Memory: {element_name} healed best with '{most_successful['strategy']}'")

        # Try most successful strategy first
        result = await self._try_strategy(state, most_successful["strategy"])
        if result:
            # Update success rate
            await self._record_heal_success(heal_key, most_successful["strategy"])
            return result

    # No history - try all strategies
    return await self._try_all_strategies(state)
```

---

### 4.5 VerdictRCA

**File**: `backend/agents/verdict_rca.py`

**Purpose**: Classify test outcomes + root cause analysis

**Current Implementation** (v1 basic):
```python
async def run(self, state: RunState) -> RunState:
    """Compute verdict based on execution results."""

    plan = state.context["plan"]
    executed = state.step_idx + 1
    total = len(plan)

    if state.failure == Failure.none and executed == total:
        state.verdict = "pass"
    elif state.failure != Failure.none:
        state.verdict = "fail"
    else:
        state.verdict = "partial"

    # Basic RCA
    state.context["verdict_summary"] = {
        "verdict": state.verdict,
        "steps_executed": executed,
        "steps_total": total,
        "heal_rounds": state.heal_round,
        "failure_type": state.failure.name if state.failure else None
    }

    return state
```

**Future Enhancements** (v2.0 - PRIORITY):

**RCA Taxonomy**:
```python
class RCAClass(Enum):
    SELECTOR_DRIFT = "selector_drift"          # Element moved/changed
    TIMING_INSTABILITY = "timing_instability"  # Timing/async issues
    ASSERTION_MISMATCH = "assertion_mismatch"  # Expected != actual
    DATA_ISSUE = "data_issue"                  # Test data problem
    ENV_FAULT = "env_fault"                    # Network/server error
    UNKNOWN = "unknown"
```

**Enhanced RCA** (v2.0):
```python
async def _analyze_root_cause(self, state):
    """Classify failure root cause."""

    failure = state.failure
    heal_rounds = state.heal_round

    # Analyze failure pattern
    if failure == Failure.discovery:
        if heal_rounds > 0 and state.verdict == "pass":
            return RCAClass.SELECTOR_DRIFT  # Healed = selector changed
        else:
            return RCAClass.SELECTOR_DRIFT  # Couldn't find element

    elif failure == Failure.timeout:
        if heal_rounds > 1:
            return RCAClass.TIMING_INSTABILITY  # Multiple retries needed
        else:
            return RCAClass.ENV_FAULT  # Network/server slow

    elif failure == Failure.gate:
        return RCAClass.SELECTOR_DRIFT  # Element state changed

    return RCAClass.UNKNOWN
```

**Memory Integration** (v3.0):
```python
async def _persist_verdict(self, state):
    """Store verdict + RCA to Postgres."""

    await db.execute("""
        INSERT INTO runs (req_id, url, verdict, heal_rounds, rca_class, finished_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
    """,
        state.req_id,
        state.context["url"],
        state.verdict,
        state.heal_round,
        self._rca_class.value
    )

    # Store step-level details
    for idx, step in enumerate(state.context["plan"]):
        await db.execute("""
            INSERT INTO run_steps (req_id, step_idx, element, action, selector, strategy, confidence, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
            state.req_id,
            idx,
            step["element"],
            step["action"],
            step.get("selector"),
            step.get("strategy"),
            step.get("confidence"),
            "success" if idx < state.step_idx else "failed"
        )
```

---

## 7. App-Specific Helpers (v2.1 NEW)

### 7.1 Architecture Pattern

**Purpose**: Keep core executor framework-agnostic while supporting complex enterprise apps

**Pattern**:
1. Create `backend/runtime/{app}_helpers.py` module
2. Implement app-specific interaction patterns
3. Import in executor, route special selectors to helpers
4. Keep core logic clean and maintainable

**Example**: Salesforce Lightning Support

**File**: `backend/runtime/salesforce_helpers.py` (312 lines)

### 7.2 Salesforce Lightning Helpers

**Multi-Strategy Combobox** (THE BREAKTHROUGH):

```python
async def handle_lightning_combobox(browser, locator, value: str) -> bool:
    """Select value from Lightning combobox with multi-strategy fallback.

    Priority order:
    1. Type-ahead (bypasses DOM quirks)
    2. aria-controls listbox targeting
    3. Keyboard navigation (rock-solid fallback)
    """

    # Strategy 1: Type-Ahead (works universally)
    try:
        await locator.click(timeout=5000)
        await browser.page.wait_for_timeout(300)

        await locator.focus()
        await browser.page.keyboard.type(value, delay=50)
        await browser.page.wait_for_timeout(200)  # Debounce

        await browser.page.keyboard.press("Enter")
        await browser.page.wait_for_timeout(300)

        # Verify selection (dropdown closed)
        element_handle = await locator.element_handle()
        aria_expanded = await element_handle.get_attribute("aria-expanded")

        if aria_expanded == "false":
            print(f"[SALESFORCE] ✅ Selected '{value}' via type-ahead")
            return True

    except Exception as e:
        print(f"[SALESFORCE] ⚠️ Type-ahead failed: {e}")

    # Strategy 2: aria-controls targeting
    try:
        return await _try_aria_controls(browser, locator, value)
    except Exception as e:
        print(f"[SALESFORCE] ⚠️ aria-controls failed: {e}")

    # Strategy 3: Keyboard navigation
    try:
        return await _try_keyboard_nav(browser, locator, value)
    except Exception as e:
        print(f"[SALESFORCE] ❌ All strategies failed: {e}")
        return False
```

**Why This Works**:
- Type-ahead bypasses DOM entirely (uses Lightning's built-in filtering)
- Works even when options aren't queryable via Playwright
- Universal solution for ALL Lightning picklist variants (standard + custom)

**Result**: 80% → 100% success rate on Salesforce Opportunity creation

**App Launcher Navigation**:
```python
async def handle_launcher_search(browser, target: str) -> bool:
    """Navigate to Salesforce object via App Launcher.

    Features:
    - Dialog-scoped search
    - Parent clickability detection
    - Retry logic with close/reopen
    """

    # Open App Launcher
    await browser.page.get_by_label("App Launcher").click()
    await browser.page.wait_for_timeout(500)

    # Search for target
    search_box = browser.page.get_by_placeholder("Search apps and items...")
    await search_box.fill(target)
    await browser.page.keyboard.press("Enter")
    await browser.page.wait_for_timeout(800)

    # Find clickable result (check parents for nested text)
    result = await _find_clickable_result(browser, target)
    if result:
        await result.click()
        return True

    return False
```

### 7.3 Future App Helpers

**SAP Fiori** (Planned):
- `backend/runtime/sap_helpers.py`
- Fiori launchpad navigation
- SAP-specific table interactions
- Multi-step business transactions

**Oracle E-Business Suite** (Planned):
- `backend/runtime/oracle_helpers.py`
- Oracle Forms handling
- Complex approval workflows
- Multi-tab navigation

**ServiceNow** (Planned):
- `backend/runtime/servicenow_helpers.py`
- Incident creation workflows
- Custom form handlers
- Knowledge base search

---

## 9. Memory & Persistence (PLANNED)

### 9.1 Why Memory is Critical

**Current Problem** (v2.1):
- No learning across test runs
- Same discovery strategies tried every time
- Healing doesn't remember what worked before
- Can't detect selector drift over time

**With Memory** (v3.0):
- **Selector Cache**: "We found 'Save' button at nth=0 last time - try that first"
- **Healing History**: "Custom picklists on this app always need type-ahead"
- **Performance Baseline**: "Discovery took 5s last week, now 15s - investigate drift"
- **Success Patterns**: "This app needs 1s page wait after navigation"

**ROI**:
- Heal rounds: 3 → 0 (system learns over time)
- Discovery speed: 2.5s → 0.3s (cache hits)
- Failure diagnosis: 10 min → 30 sec (historical context)

### 9.2 Postgres Schema

```sql
-- Runs table: One row per test execution
CREATE TABLE runs (
    req_id VARCHAR(100) PRIMARY KEY,
    url TEXT NOT NULL,
    verdict VARCHAR(20) CHECK (verdict IN ('pass', 'fail', 'partial')),
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    heal_rounds INTEGER DEFAULT 0,
    rca_class VARCHAR(50),  -- selector_drift, timing_instability, etc.
    rca_confidence DECIMAL(3,2),
    rca_message TEXT,
    total_duration_ms INTEGER,

    -- Indexes for queries
    INDEX idx_verdict (verdict),
    INDEX idx_started_at (started_at DESC),
    INDEX idx_rca_class (rca_class)
);

-- Steps table: One row per step executed
CREATE TABLE run_steps (
    id SERIAL PRIMARY KEY,
    req_id VARCHAR(100) REFERENCES runs(req_id) ON DELETE CASCADE,
    step_idx INTEGER,
    element VARCHAR(200),
    action VARCHAR(50),
    selector TEXT,
    strategy VARCHAR(50),  -- label, placeholder, role_name, cached
    confidence DECIMAL(3,2),
    status VARCHAR(20) CHECK (status IN ('success', 'failed')),
    heal_round INTEGER DEFAULT 0,
    error_message TEXT,
    duration_ms INTEGER,
    executed_at TIMESTAMP DEFAULT NOW(),

    -- Indexes
    INDEX idx_req_id (req_id),
    INDEX idx_status (status)
);

-- Artifacts table: Generated test files + screenshots
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    req_id VARCHAR(100) REFERENCES runs(req_id) ON DELETE CASCADE,
    artifact_type VARCHAR(50),  -- 'test_file', 'screenshot', 'verdict_report'
    file_path TEXT,
    file_hash VARCHAR(64),
    size_bytes INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_req_id (req_id)
);

-- Metrics table: Granular performance metrics
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    req_id VARCHAR(100) REFERENCES runs(req_id) ON DELETE CASCADE,
    metric_name VARCHAR(100),  -- 'discovery_time_ms', 'action_time_ms', etc.
    metric_value DECIMAL(10,2),
    step_idx INTEGER,  -- NULL for run-level metrics
    recorded_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_req_id (req_id),
    INDEX idx_metric_name (metric_name)
);

-- Selector cache table: Persistent POM cache
CREATE TABLE selector_cache (
    id SERIAL PRIMARY KEY,
    url_pattern TEXT,     -- e.g., "https://saucedemo.com/%"
    element_name VARCHAR(200),
    selector TEXT,
    strategy VARCHAR(50),
    confidence DECIMAL(3,2),
    hit_count INTEGER DEFAULT 0,
    last_verified_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (url_pattern, element_name),
    INDEX idx_url_pattern (url_pattern),
    INDEX idx_last_verified (last_verified_at DESC)
);

-- Healing history: Track what strategies work
CREATE TABLE heal_history (
    id SERIAL PRIMARY KEY,
    element_name VARCHAR(200),
    url_pattern TEXT,
    strategy VARCHAR(50),
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_heal_time_ms INTEGER,
    last_used_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (element_name, url_pattern, strategy),
    INDEX idx_element_name (element_name)
);
```

### 9.3 Redis Caching Strategy

**Purpose**: Fast ephemeral state for current runs

```python
# POM cache (short-term selector memory)
# Key: f"pom:{url}:{element}"
# Value: JSON with selector, confidence, strategy
# TTL: 3600s (1 hour)
pom:https://saucedemo.com:Username → {
    "selector": "#user-name",
    "confidence": 0.92,
    "strategy": "placeholder",
    "last_verified": 1698765432
}

# LangGraph checkpoints (state persistence)
# Key: f"checkpoint:{req_id}"
# Value: Pickled RunState
# TTL: 86400s (24 hours)
checkpoint:REQ-001 → <pickled RunState>

# Healing counters (per-run tracking)
# Key: f"heal:{req_id}:{selector}"
# Value: Integer count
# TTL: 3600s (1 hour)
heal:REQ-001:#button-save → 2

# Rate limiting
# Key: f"rate:{client_id}"
# Value: Request count
# TTL: 60s (sliding window)
rate:client_123 → 15

# Discovery locks (prevent duplicate discovery)
# Key: f"lock:discovery:{url}:{element}"
# Value: req_id holding lock
# TTL: 30s (prevent stuck locks)
lock:discovery:https://app.com:SaveButton → REQ-123
```

### 9.4 Memory Integration Examples

**POMBuilder with Cache**:
```python
async def _discover_with_cache(self, browser, step):
    """Check cache before running discovery."""

    element = step["element"]
    url = browser.page.url

    # Try Redis cache (fast)
    cache_key = f"pom:{url}:{element}"
    cached = await redis.get(cache_key)

    if cached:
        data = json.loads(cached)
        selector = data["selector"]

        # Validate cached selector still works
        if await self._validate_selector(browser, selector):
            logger.info(f"[POM] ✅ Cache HIT: {element}")
            return {
                "selector": selector,
                "score": data["confidence"] + 0.05,  # Boost for cache
                "meta": {"strategy": "cached"}
            }

    # Try Postgres persistent cache (slower but long-term memory)
    db_cached = await db.fetchrow("""
        SELECT selector, strategy, confidence
        FROM selector_cache
        WHERE url_pattern = $1 AND element_name = $2
        AND last_verified_at > NOW() - INTERVAL '7 days'
        ORDER BY hit_count DESC
        LIMIT 1
    """, f"{url}%", element)

    if db_cached:
        selector = db_cached["selector"]
        if await self._validate_selector(browser, selector):
            logger.info(f"[POM] ✅ DB Cache HIT: {element}")

            # Update hit count
            await db.execute("""
                UPDATE selector_cache
                SET hit_count = hit_count + 1, last_verified_at = NOW()
                WHERE url_pattern = $1 AND element_name = $2
            """, f"{url}%", element)

            # Warm Redis cache
            await redis.setex(cache_key, 3600, json.dumps({
                "selector": selector,
                "confidence": db_cached["confidence"],
                "strategy": db_cached["strategy"]
            }))

            return {
                "selector": selector,
                "score": db_cached["confidence"] + 0.03,
                "meta": {"strategy": "db_cached"}
            }

    # No cache - run full discovery
    result = await self._full_discovery(browser, step)

    if result:
        # Store in both caches
        await self._cache_selector(url, element, result)

    return result
```

**OracleHealer with Healing History**:
```python
async def _heal_with_history(self, state):
    """Use past healing successes to inform strategy."""

    failed_step = state.context["plan"][state.step_idx]
    element = failed_step["element"]
    url = state.context["url"]

    # Query healing history
    history = await db.fetch("""
        SELECT strategy, success_count, failure_count, avg_heal_time_ms
        FROM heal_history
        WHERE element_name = $1 AND url_pattern LIKE $2
        ORDER BY (success_count::float / NULLIF(failure_count + success_count, 0)) DESC
        LIMIT 3
    """, element, f"{url}%")

    if history:
        # Try most successful strategy first
        best = history[0]
        logger.info(f"[HEALER] 📚 Memory: '{element}' healed best with '{best['strategy']}' ({best['success_count']} successes)")

        result = await self._try_strategy(state, best["strategy"])

        if result:
            # Record success
            await self._record_heal_outcome(element, url, best["strategy"], success=True)
            return result
        else:
            # Record failure, try next best
            await self._record_heal_outcome(element, url, best["strategy"], success=False)

            if len(history) > 1:
                result = await self._try_strategy(state, history[1]["strategy"])
                if result:
                    await self._record_heal_outcome(element, url, history[1]["strategy"], success=True)
                    return result

    # No history - try all strategies
    return await self._try_all_strategies(state)
```

---

## 10. Telemetry Integration (PLANNED)

### 10.1 Why Telemetry is Critical

**Current Problem** (v2.1):
- Debugging = log archaeology (print statements)
- No distributed tracing (can't follow request across agents)
- No performance monitoring (can't identify bottlenecks)
- No replay capability (can't reproduce failures)

**With Telemetry** (v3.0):
- **Distributed Tracing**: Follow req_id across all agents in LangSmith
- **Performance Monitoring**: Identify slow discovery strategies, optimize them
- **Replay Capability**: Re-run exact scenario from trace data
- **Trend Analysis**: Detect selector drift before tests fail

**ROI**:
- Debug time: 10 min → 30 sec (structured traces)
- Performance optimization: Find 20% slowest operations, fix them
- Proactive alerts: "Discovery times increased 3x this week"

### 10.2 LangSmith Integration

**Architecture**:
```
PACTS Agent → LangSmith Tracer → LangSmith Cloud
                    ↓
             Local spans.json (backup)
```

**Span Structure**:
```python
# Root span (one per test run)
{
    "trace_id": "tr_abc123",
    "span_id": "sp_root",
    "name": "pacts_run",
    "kind": "workflow",
    "start_time": "2025-11-02T10:00:00Z",
    "end_time": "2025-11-02T10:00:15Z",
    "duration_ms": 15000,
    "tags": {
        "req_id": "REQ-LOGIN-001",
        "url": "https://saucedemo.com",
        "verdict": "pass"
    },
    "children": [...]  # Agent spans
}

# Agent span (one per agent invocation)
{
    "span_id": "sp_planner",
    "parent_span_id": "sp_root",
    "name": "planner",
    "kind": "agent",
    "start_time": "2025-11-02T10:00:00Z",
    "duration_ms": 1200,
    "tags": {
        "agent": "planner",
        "steps_parsed": 3
    },
    "events": [
        {"time": "2025-11-02T10:00:00.5Z", "name": "parsed_step", "data": {"element": "Username"}},
        {"time": "2025-11-02T10:00:01.0Z", "name": "parsed_step", "data": {"element": "Password"}}
    ]
}

# Step span (one per test step)
{
    "span_id": "sp_step_0",
    "parent_span_id": "sp_executor",
    "name": "step:fill_Username",
    "kind": "action",
    "start_time": "2025-11-02T10:00:05Z",
    "duration_ms": 850,
    "tags": {
        "step_idx": 0,
        "element": "Username",
        "action": "fill",
        "selector": "#user-name",
        "strategy": "placeholder",
        "confidence": 0.88,
        "status": "success"
    }
}
```

**Implementation**:
```python
# backend/runtime/telemetry.py

from langsmith import Client
from langsmith.run_trees import RunTree
import os

class PACTSTracer:
    """LangSmith telemetry integration."""

    def __init__(self):
        self.client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))
        self.project = "pacts-production"
        self.current_run = None

    def start_run(self, req_id: str, url: str):
        """Start root span for test run."""
        self.current_run = RunTree(
            name="pacts_run",
            run_type="chain",
            project_name=self.project,
            tags=["pacts", "v2.1"],
            metadata={
                "req_id": req_id,
                "url": url,
                "version": "2.1"
            }
        )
        self.current_run.post()

    def start_agent(self, agent_name: str):
        """Start agent span."""
        if not self.current_run:
            return None

        agent_run = self.current_run.create_child(
            name=agent_name,
            run_type="llm" if agent_name in ["planner", "oracle_healer", "verdict_rca"] else "tool"
        )
        agent_run.post()
        return agent_run

    def end_agent(self, agent_run, outputs: dict):
        """End agent span with outputs."""
        if agent_run:
            agent_run.end(outputs=outputs)
            agent_run.patch()

    def log_step(self, step_idx: int, element: str, action: str, selector: str,
                 strategy: str, confidence: float, status: str, duration_ms: int):
        """Log step execution."""
        if not self.current_run:
            return

        step_run = self.current_run.create_child(
            name=f"step:{action}_{element}",
            run_type="tool",
            metadata={
                "step_idx": step_idx,
                "element": element,
                "action": action,
                "selector": selector,
                "strategy": strategy,
                "confidence": confidence,
                "status": status,
                "duration_ms": duration_ms
            }
        )
        step_run.post()
        step_run.end(outputs={"status": status})
        step_run.patch()

    def end_run(self, verdict: str, heal_rounds: int, total_duration_ms: int):
        """End root span with verdict."""
        if self.current_run:
            self.current_run.end(outputs={
                "verdict": verdict,
                "heal_rounds": heal_rounds,
                "total_duration_ms": total_duration_ms
            })
            self.current_run.patch()


# Usage in agents
# backend/agents/executor.py

from ..runtime.telemetry import PACTSTracer

async def run(self, state: RunState) -> RunState:
    """Execute with telemetry."""

    tracer = state.context.get("tracer")
    if not tracer:
        tracer = PACTSTracer()
        state.context["tracer"] = tracer
        tracer.start_run(state.req_id, state.context["url"])

    agent_run = tracer.start_agent("executor")

    try:
        # Execute steps
        for idx, step in enumerate(state.context["plan"]):
            start_time = time.time()

            # Execute action
            result = await self._execute_step(state, step)

            duration_ms = int((time.time() - start_time) * 1000)

            # Log to telemetry
            tracer.log_step(
                step_idx=idx,
                element=step["element"],
                action=step["action"],
                selector=step["selector"],
                strategy=step["strategy"],
                confidence=step["confidence"],
                status="success" if result else "failed",
                duration_ms=duration_ms
            )

            if not result:
                state.failure = Failure.timeout
                state.step_idx = idx
                break

        tracer.end_agent(agent_run, {"steps_executed": state.step_idx + 1})

    except Exception as e:
        tracer.end_agent(agent_run, {"error": str(e)})
        raise

    return state
```

### 10.3 Telemetry Queries

**LangSmith Dashboard Queries**:

1. **Average discovery time by strategy**:
```python
runs = client.list_runs(
    project_name="pacts-production",
    filter='metadata.strategy = "placeholder"'
)
avg_time = sum(r.execution_time for r in runs) / len(runs)
```

2. **Selector drift detection**:
```python
# Compare confidence scores over time
recent = client.list_runs(
    project_name="pacts-production",
    filter='start_time > "2025-11-01" AND metadata.element = "SaveButton"'
)
old = client.list_runs(
    project_name="pacts-production",
    filter='start_time < "2025-10-01" AND metadata.element = "SaveButton"'
)

recent_confidence = [r.metadata["confidence"] for r in recent]
old_confidence = [r.metadata["confidence"] for r in old]

# Alert if confidence dropped by >10%
if avg(recent_confidence) < avg(old_confidence) - 0.10:
    alert("Selector drift detected for SaveButton")
```

3. **Healing effectiveness**:
```python
healed_runs = client.list_runs(
    project_name="pacts-production",
    filter='metadata.heal_rounds > 0 AND metadata.verdict = "pass"'
)

heal_success_rate = len(healed_runs) / total_runs_with_failures
```

---

## 11. Observability API (PLANNED)

### 11.1 Why API is Critical

**Current Problem** (v2.1):
- No programmatic access to test results
- Can't query historical data
- No integration with CI/CD pipelines
- No dashboards for stakeholders

**With API** (v3.0):
- **REST endpoints**: Query runs, steps, verdicts, artifacts
- **CI/CD integration**: Jenkins/GitHub Actions can query results
- **Dashboard**: Real-time monitoring of test health
- **Alerts**: Notify on failure trends, selector drift

**ROI**:
- Integration time: 2 days → 2 hours (REST API vs. custom scripts)
- Visibility: Stakeholders see test health in real-time
- Alerting: Proactive notification on trends

### 11.2 FastAPI Endpoints

**File**: `backend/api/main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncpg

app = FastAPI(title="PACTS API v1.0")

# Database connection pool
db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(
        host="localhost",
        database="pacts",
        user="pacts_user",
        password=os.getenv("DB_PASSWORD")
    )

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()


# Models
class RunRequest(BaseModel):
    req_id: str
    url: str
    steps: List[str]  # ["Username | fill | standard_user", ...]

class RunResponse(BaseModel):
    req_id: str
    status: str  # "queued", "running", "completed"
    message: str

class RunSummary(BaseModel):
    req_id: str
    url: str
    verdict: str
    started_at: str
    finished_at: Optional[str]
    heal_rounds: int
    total_steps: int
    executed_steps: int

class StepDetail(BaseModel):
    step_idx: int
    element: str
    action: str
    selector: str
    strategy: str
    confidence: float
    status: str
    heal_round: int
    duration_ms: int


# Endpoints

@app.post("/run", response_model=RunResponse, status_code=202)
async def start_run(request: RunRequest):
    """Start a PACTS test run."""

    # Validate req_id uniqueness
    existing = await db_pool.fetchval(
        "SELECT req_id FROM runs WHERE req_id = $1", request.req_id
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"req_id '{request.req_id}' already exists")

    # Insert placeholder row
    await db_pool.execute("""
        INSERT INTO runs (req_id, url, verdict, started_at)
        VALUES ($1, $2, 'running', NOW())
    """, request.req_id, request.url)

    # Queue execution (background task)
    background_tasks.add_task(execute_pacts, request)

    return RunResponse(
        req_id=request.req_id,
        status="queued",
        message="PACTS execution started"
    )


@app.get("/runs/{req_id}", response_model=RunSummary)
async def get_run(req_id: str):
    """Get run summary."""

    row = await db_pool.fetchrow("""
        SELECT req_id, url, verdict, started_at, finished_at, heal_rounds
        FROM runs
        WHERE req_id = $1
    """, req_id)

    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{req_id}' not found")

    # Count steps
    step_counts = await db_pool.fetchrow("""
        SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE status = 'success') as executed
        FROM run_steps
        WHERE req_id = $1
    """, req_id)

    return RunSummary(
        req_id=row["req_id"],
        url=row["url"],
        verdict=row["verdict"],
        started_at=row["started_at"].isoformat(),
        finished_at=row["finished_at"].isoformat() if row["finished_at"] else None,
        heal_rounds=row["heal_rounds"],
        total_steps=step_counts["total"],
        executed_steps=step_counts["executed"]
    )


@app.get("/runs/{req_id}/steps", response_model=List[StepDetail])
async def get_steps(req_id: str):
    """Get detailed step execution history."""

    rows = await db_pool.fetch("""
        SELECT step_idx, element, action, selector, strategy, confidence, status, heal_round, duration_ms
        FROM run_steps
        WHERE req_id = $1
        ORDER BY step_idx
    """, req_id)

    if not rows:
        raise HTTPException(status_code=404, detail=f"No steps found for run '{req_id}'")

    return [StepDetail(**dict(row)) for row in rows]


@app.get("/runs", response_model=List[RunSummary])
async def list_runs(
    verdict: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List recent runs with optional filtering."""

    query = "SELECT req_id, url, verdict, started_at, finished_at, heal_rounds FROM runs"
    params = []

    if verdict:
        query += " WHERE verdict = $1"
        params.append(verdict)

    query += " ORDER BY started_at DESC LIMIT $2 OFFSET $3"
    params.extend([limit, offset])

    rows = await db_pool.fetch(query, *params)

    results = []
    for row in rows:
        # Count steps
        step_counts = await db_pool.fetchrow("""
            SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE status = 'success') as executed
            FROM run_steps
            WHERE req_id = $1
        """, row["req_id"])

        results.append(RunSummary(
            req_id=row["req_id"],
            url=row["url"],
            verdict=row["verdict"],
            started_at=row["started_at"].isoformat(),
            finished_at=row["finished_at"].isoformat() if row["finished_at"] else None,
            heal_rounds=row["heal_rounds"],
            total_steps=step_counts["total"],
            executed_steps=step_counts["executed"]
        ))

    return results


@app.get("/artifacts/{req_id}")
async def get_artifacts(req_id: str):
    """Get generated test file and artifacts."""

    rows = await db_pool.fetch("""
        SELECT artifact_type, file_path, file_hash, size_bytes
        FROM artifacts
        WHERE req_id = $1
    """, req_id)

    if not rows:
        raise HTTPException(status_code=404, detail=f"No artifacts found for run '{req_id}'")

    return {
        "req_id": req_id,
        "artifacts": [dict(row) for row in rows]
    }


@app.get("/health")
async def health():
    """Service health check."""

    # Check database
    try:
        await db_pool.fetchval("SELECT 1")
        db_status = "connected"
    except:
        db_status = "error"

    # Check Redis
    try:
        await redis.ping()
        redis_status = "connected"
    except:
        redis_status = "error"

    return {
        "status": "healthy" if db_status == "connected" and redis_status == "connected" else "degraded",
        "version": "2.1.0",
        "services": {
            "postgres": db_status,
            "redis": redis_status,
            "playwright": "ready"
        }
    }


@app.get("/metrics")
async def get_metrics():
    """Get aggregated metrics."""

    stats = await db_pool.fetchrow("""
        SELECT
            COUNT(*) as total_runs,
            COUNT(*) FILTER (WHERE verdict = 'pass') as passed,
            COUNT(*) FILTER (WHERE verdict = 'fail') as failed,
            AVG(heal_rounds) as avg_heal_rounds,
            AVG(EXTRACT(EPOCH FROM (finished_at - started_at)) * 1000) as avg_duration_ms
        FROM runs
        WHERE started_at > NOW() - INTERVAL '7 days'
    """)

    return {
        "period": "last_7_days",
        "total_runs": stats["total_runs"],
        "passed": stats["passed"],
        "failed": stats["failed"],
        "pass_rate": stats["passed"] / stats["total_runs"] if stats["total_runs"] > 0 else 0,
        "avg_heal_rounds": float(stats["avg_heal_rounds"]) if stats["avg_heal_rounds"] else 0,
        "avg_duration_ms": float(stats["avg_duration_ms"]) if stats["avg_duration_ms"] else 0
    }


@app.get("/metrics/discovery")
async def get_discovery_metrics():
    """Get discovery strategy performance metrics."""

    stats = await db_pool.fetch("""
        SELECT
            strategy,
            COUNT(*) as total_uses,
            AVG(confidence) as avg_confidence,
            AVG(duration_ms) as avg_duration_ms,
            COUNT(*) FILTER (WHERE status = 'success') as successes
        FROM run_steps
        WHERE executed_at > NOW() - INTERVAL '7 days'
        GROUP BY strategy
        ORDER BY total_uses DESC
    """)

    return {
        "period": "last_7_days",
        "strategies": [
            {
                "strategy": row["strategy"],
                "total_uses": row["total_uses"],
                "avg_confidence": float(row["avg_confidence"]),
                "avg_duration_ms": float(row["avg_duration_ms"]) if row["avg_duration_ms"] else 0,
                "success_rate": row["successes"] / row["total_uses"]
            }
            for row in stats
        ]
    }
```

### 11.3 CI/CD Integration Examples

**GitHub Actions**:
```yaml
name: PACTS Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run PACTS Tests
        run: |
          # Start PACTS run
          REQ_ID="CI-$(date +%s)"
          curl -X POST http://pacts-api:8000/run \
            -H "Content-Type: application/json" \
            -d '{
              "req_id": "'$REQ_ID'",
              "url": "https://staging.example.com",
              "steps": ["Username | fill | testuser", "Password | fill | pass123", "Login | click"]
            }'

          # Poll for completion
          while true; do
            STATUS=$(curl -s http://pacts-api:8000/runs/$REQ_ID | jq -r '.verdict')
            if [ "$STATUS" != "running" ]; then
              break
            fi
            sleep 5
          done

          # Check verdict
          if [ "$STATUS" = "pass" ]; then
            echo "✅ PACTS tests passed"
            exit 0
          else
            echo "❌ PACTS tests failed"
            curl -s http://pacts-api:8000/runs/$REQ_ID/steps | jq '.'
            exit 1
          fi
```

**Jenkins Pipeline**:
```groovy
pipeline {
    agent any

    stages {
        stage('PACTS Tests') {
            steps {
                script {
                    def reqId = "JENKINS-${BUILD_NUMBER}"

                    // Start PACTS run
                    sh """
                        curl -X POST ${PACTS_API_URL}/run \
                          -H "Content-Type: application/json" \
                          -d '{"req_id": "${reqId}", "url": "${STAGING_URL}", "steps": [...]}'
                    """

                    // Wait for completion
                    timeout(time: 5, unit: 'MINUTES') {
                        waitUntil {
                            def response = sh(
                                script: "curl -s ${PACTS_API_URL}/runs/${reqId}",
                                returnStdout: true
                            ).trim()
                            def json = readJSON text: response
                            return json.verdict != 'running'
                        }
                    }

                    // Get verdict
                    def verdict = sh(
                        script: "curl -s ${PACTS_API_URL}/runs/${reqId} | jq -r '.verdict'",
                        returnStdout: true
                    ).trim()

                    if (verdict != 'pass') {
                        error("PACTS tests failed with verdict: ${verdict}")
                    }
                }
            }
        }
    }
}
```

---

## 13. Implementation Roadmap

### Phase 1: Foundation (COMPLETE ✅)

**Duration**: 2 weeks
**Status**: ✅ Production Ready

**Deliverables**:
- [x] 6-agent architecture (Planner, POMBuilder, Generator, Executor, OracleHealer, VerdictRCA)
- [x] LangGraph 1.0 orchestration
- [x] Discovery strategies (label, placeholder, role_name)
- [x] Five-point actionability gate
- [x] SauceDemo validation (3/3 steps)
- [x] Pattern-based execution (autocomplete, activator)

---

### Phase 2: Production Sites (COMPLETE ✅)

**Duration**: 3 weeks
**Status**: ✅ Production Ready

**Deliverables**:
- [x] Wikipedia validation (autocomplete pattern)
- [x] GitHub validation (activator pattern)
- [x] Amazon validation (e-commerce search)
- [x] eBay validation (e-commerce search)
- [x] Fillable element filtering
- [x] Pattern registry architecture

---

### Phase 2.1: Enterprise SPA Support (COMPLETE ✅)

**Duration**: 1 week
**Status**: ✅ Production Ready

**Deliverables**:
- [x] Salesforce Lightning support (10/10 steps)
- [x] Multi-strategy Lightning combobox (type-ahead breakthrough)
- [x] App-specific helpers architecture
- [x] SPA page load wait strategy
- [x] Session reuse (HITL + cookie persistence)
- [x] Parent clickability detection

**Achievements**:
- 100% success rate across 6 production sites
- 0 heal rounds average
- 73.7 hours/year saved per developer (session reuse)
- Framework-agnostic design (34% code reduction)

---

### Phase 3: Memory & Persistence (PRIORITY 🚧)

**Duration**: 2 weeks
**Status**: 🚧 Planned

**Deliverables**:
- [ ] Postgres schema implementation
- [ ] Redis caching layer
- [ ] POMBuilder cache integration
- [ ] OracleHealer healing history
- [ ] Selector cache table + hit counting
- [ ] Database migrations (Alembic)

**Success Criteria**:
- Cache hit rate >60% after 100 runs
- Heal rounds reduced from 3 → 1 average
- Discovery time reduced by 50% (cache hits)

**Implementation Priority**:
1. **Week 1**: Postgres schema + basic CRUD
   - Create tables (runs, run_steps, artifacts, metrics)
   - Implement database client wrapper
   - VerdictRCA persistence integration

2. **Week 2**: Redis caching + memory integration
   - POM cache (selector cache)
   - LangGraph checkpoints
   - POMBuilder cache-first discovery
   - OracleHealer healing history

---

### Phase 4: Telemetry & Observability (HIGH PRIORITY 🚧)

**Duration**: 2 weeks
**Status**: 🚧 Planned

**Deliverables**:
- [ ] LangSmith integration (distributed tracing)
- [ ] Span instrumentation (all agents)
- [ ] Performance monitoring dashboards
- [ ] Selector drift detection queries
- [ ] Healing effectiveness analytics

**Success Criteria**:
- All runs traced to LangSmith
- Query interface for historical analysis
- Drift detection alerts (<10 min lag)

**Implementation Priority**:
1. **Week 1**: LangSmith integration
   - Tracer implementation
   - Root span + agent spans
   - Step-level instrumentation

2. **Week 2**: Analytics + queries
   - Dashboard queries (discovery time, heal rate)
   - Drift detection logic
   - Alert integration (Slack/email)

---

### Phase 5: Observability API (HIGH PRIORITY 🚧)

**Duration**: 1.5 weeks
**Status**: 🚧 Planned

**Deliverables**:
- [ ] FastAPI REST endpoints
- [ ] `/run`, `/runs/{id}`, `/runs/{id}/steps`, `/artifacts/{id}`
- [ ] `/health`, `/metrics`, `/metrics/discovery`
- [ ] CI/CD integration examples (GitHub Actions, Jenkins)
- [ ] API documentation (Swagger/OpenAPI)

**Success Criteria**:
- All endpoints functional + tested
- CI/CD integration working
- API documentation complete

**Implementation Priority**:
1. **Week 1**: Core endpoints
   - POST /run (async execution)
   - GET /runs/{id} (summary)
   - GET /runs/{id}/steps (detail)
   - GET /health

2. **Week 2**: Analytics endpoints + CI/CD
   - GET /metrics (aggregated stats)
   - GET /metrics/discovery (strategy performance)
   - GitHub Actions example
   - Jenkins pipeline example

---

### Phase 6: Advanced Healing (v2.0) (FUTURE)

**Duration**: 2 weeks
**Status**: 📋 Backlog

**Deliverables**:
- [ ] OracleHealer v2.0 (reveal, reprobe, stability waits)
- [ ] Adaptive timeout strategies
- [ ] Scroll-into-view + z-index overlay handling
- [ ] Multi-strategy reprobe (try all discovery strategies)

**Success Criteria**:
- Heal success rate >80% (from 50% v1)
- Average heal time <2 seconds

---

### Phase 7: Additional Enterprise Apps (FUTURE)

**Duration**: 1 week per app
**Status**: 📋 Backlog

**Deliverables**:
- [ ] SAP Fiori helper module
- [ ] Oracle E-Business Suite helper module
- [ ] ServiceNow helper module
- [ ] Workday helper module

**Pattern**: Follow Salesforce helpers model (type-ahead, app-specific navigation, custom components)

---

### Phase 8: Dashboard & UI (FUTURE)

**Duration**: 3 weeks
**Status**: 📋 Backlog

**Deliverables**:
- [ ] React dashboard (real-time test monitoring)
- [ ] Historical run visualization
- [ ] Selector drift alerts
- [ ] Healing analytics charts
- [ ] Test artifact viewer (screenshots, videos)

---

## Summary

**Current State (v2.1)**:
- ✅ 6-agent architecture production-ready
- ✅ 100% success rate (6/6 production sites including Salesforce Lightning)
- ✅ 0 heal rounds average
- ✅ App-specific helpers pattern established

**Critical Next Steps (v3.0)**:
1. **Memory & Persistence** (2 weeks) - Enables learning across runs
2. **Telemetry Integration** (2 weeks) - Enables observability & debugging
3. **Observability API** (1.5 weeks) - Enables CI/CD integration

**Total Timeline to v3.0**: ~5.5 weeks

**ROI**:
- **Memory**: 3 → 0 heal rounds (faster tests)
- **Telemetry**: 10 min → 30 sec debug time (faster fixes)
- **API**: 2 days → 2 hours integration time (faster adoption)

---

## Addendum A: Version & Environment Matrix

### Platform Requirements

**Python Runtime**: 3.11.x series
- CI environments pin to 3.11.9 for reproducibility
- Production minimum: 3.11.0

**Playwright**: 1.48.x series
- Browsers: Chromium, WebKit (Firefox optional)
- Execution modes: Both headed and headless supported
- Browser stability verified on 1.48.0+

**LangGraph**: 0.4.10
- Forward-compatible with 1.0 API
- LangChain dependencies managed as transitive (pinned by LangGraph)

**Operating Systems**:
- Windows 11 (CI runners + developer workstations)
- Ubuntu 22.04 LTS (CI runners)
- macOS support: Best effort (not in CI pipeline)

**Node.js**: 20.x (tools only)
- Required for Playwright installation
- Not used in runtime execution

### Upgrade Policy

**Frequency**: Quarterly dependency updates
**Process**:
1. Create feature branch with updated dependencies
2. Run full smoke test suite
3. Promote to main if all tests pass
4. Update version matrix documentation

---

## Addendum B: Service Level Objectives (SLOs) & Run Policies

### Success Rate Targets

**Smoke Tests**: ≥ 98% pass rate
- Quick validation suite (Wikipedia, GitHub, Amazon, eBay, SauceDemo)
- Must complete within 5 minutes
- Used as merge gate for pull requests

**Regression Suite**: ≥ 95% pass rate
- Full enterprise test suite including Salesforce
- Nightly execution schedule
- Includes complex multi-step workflows

### Performance Targets

**Step Execution Time**:
- p95 ≤ 2.5 seconds (smoke tests)
- p95 ≤ 4.0 seconds (Salesforce enterprise workflows)

**Healing Behavior**:
- Target: 0.0 heal rounds per test
- Maximum allowed: ≤ 1 heal round
- Policy: If healing exceeds 1 round, mark test as failed (indicates selector instability)

**Flake Tolerance**:
- Maximum rerun rate: <1% per week
- Quarantine tests exceeding threshold until root cause resolved

### Merge Gate Requirements

Before any code merges to main:
1. All smoke tests must pass (green status)
2. Healing rounds = 0 (no self-correction needed)
3. Total execution duration ≤ budget (5 minutes for smoke suite)

---

## Addendum C: Selector Memory Semantics (v3.0)

### Cache Key Structure

**Format**: `(domain, path_pattern, target_fingerprint)`

**Example**:
- Domain: `saucedemo.com`
- Path pattern: `/inventory.html`
- Target fingerprint: `role=button[name*="add-to-cart"]`

### Time-to-Live (TTL) Strategy

**Default TTL**: 7 days
- Assumption: Most UIs stable for at least one week
- Automatically extends on successful cache hits

**Dynamic Module TTL**: 24 hours
- For pages with frequent updates (dashboards, feeds)
- Detected via high DOM change rate

**Stable Admin Pages TTL**: 30 days
- For rarely-changing interfaces (settings, configuration)
- Validated via low DOM change rate over time

### Cache Eviction Policy

**Strategy**: Least Recently Used (LRU)
**Capacity**: 10,000 entries maximum
**Behavior**: Evict oldest unused selectors when capacity reached

### Drift Detection & Invalidation

**Invalidation Triggers**:
1. **Two consecutive misses**: Selector fails validation twice in a row
2. **DOM hash change >35%**: Structural page changes detected
3. **Manual invalidation**: Via API or admin interface

**Drift Detection**:
- Calculate DOM fingerprint (tag structure hash)
- Compare against cached baseline
- If delta exceeds 35%, invalidate entire page cache

### Region Scoping

**Scope Awareness**: Respect `within` region hints
**Cache Structure**:
- Store region-root element selector
- Store relative locator from region root
- Enables cache hits even when absolute page structure changes

**Example**:
```
Cached: within="App Launcher" → role=link[name*="Opportunities"]
Reusable across different Lightning pages that contain App Launcher
```

---

## Addendum D: Telemetry Specification

### Span Taxonomy

**Hierarchy**:
```
run (root span)
  ├─ agent (planner, pom_builder, executor, etc.)
  │   └─ step (individual test step)
  └─ healer (if triggered)
      └─ retry_attempt
```

### Required Tags (All Spans)

**Run-level tags**:
- `suite`: Test suite name (e.g., "salesforce_opportunity_hitl")
- `req_id`: Unique request identifier
- `url`: Target application URL

**Step-level tags**:
- `action`: Action type (click, fill, select, etc.)
- `target`: Element identifier with role/name
- `within`: Region scope (if applicable)
- `engine`: Execution engine (local_playwright | mcp)
- `gates`: Five-point gate results (unique/visible/enabled/stable/scoped)
- `retries`: Number of retry attempts
- `duration_ms`: Step execution time in milliseconds

### Data Redaction Policy

**Value Masking**:
- Mask all input field values in traces
- Replace with placeholder: `***REDACTED***`
- Exception: Public test data explicitly marked as non-sensitive

**URL Hashing**:
- Hash URLs containing session tokens or user identifiers
- Preserve domain and path structure for analysis
- Example: `https://app.com/user/abc123` → `https://app.com/user/[HASH:a1b2c3]`

**Screenshot Blurring**:
- Apply 8px Gaussian blur to PII zones
- Zones: Input fields, authentication tokens, email addresses
- Preserve UI structure for debugging

### Output Formats

**JSONL Log** (per test run):
- One JSON object per line
- Includes all spans with full metadata
- Stored in: `logs/runs/{req_id}.jsonl`

**HTML Evidence Report**:
- Human-readable summary of test execution
- Embedded screenshots with annotations
- Trace timeline visualization
- Verdict summary with RCA classification
- Stored in: `reports/{req_id}.html`

---

## Addendum E: Security & Privacy

### Secret Management

**Storage Policy**:
- All secrets stored in environment variables or CI vault
- Never log secrets in console output or trace files
- Rotate credentials quarterly

**Prohibited Locations**:
- ❌ Source code
- ❌ Configuration files committed to git
- ❌ Log files or telemetry data
- ❌ Screenshot artifacts

### Screenshot Redaction

**Automatic Redaction Zones**:
- Input fields (type=password, email, text with sensitive patterns)
- Authentication tokens (detected via regex patterns)
- Email addresses (PII detection)

**Redaction Method**:
- 8px Gaussian blur applied to bounding box
- Alternative: Black rectangle overlay (configurable)

### Multi-Tenancy & Isolation

**Database Isolation**: Schema-per-project
- Each customer/project gets dedicated Postgres schema
- No cross-contamination of test data
- Enforced at connection pool level

**Tenant Separation**:
- Selector cache isolated by schema
- Telemetry data partitioned by project_id
- No shared resources across tenants

### Audit Logging

**Audited Events**:
1. Feature flag changes (e.g., enabling MCP actions)
2. HITL manual overrides (human intervention during test)
3. MCP mode changes (discovery-only ↔ actions-enabled)
4. Credential rotations

**Audit Log Format**:
```json
{
  "timestamp": "2025-11-02T14:30:00Z",
  "event_type": "feature_flag_change",
  "user": "admin@company.com",
  "resource": "MCP_ACTIONS_ENABLED",
  "old_value": false,
  "new_value": true,
  "justification": "Enabling for beta testing"
}
```

---

## Addendum F: Cost & Safety Rails

### LLM Token Limits

**Hard Cap**: 60,000 tokens per test run
- Prevents runaway costs from infinite loops
- Typical run usage: 5,000-15,000 tokens

**Soft Warning**: 45,000 tokens
- Log warning when threshold crossed
- Helps identify inefficient prompting strategies

### Model Fallback Chain

**Priority Order**:
1. **Claude Haiku 3.5** (primary)
   - Fast, cost-effective
   - Used for Planner, OracleHealer, VerdictRCA
2. **Claude Sonnet Mini** (fallback #1)
   - If Haiku unavailable or rate-limited
3. **GPT-4o Mini** (fallback #2)
   - Last resort if Anthropic services unavailable

**Fallback Trigger**: HTTP 429 (rate limit) or 503 (service unavailable)

### Circuit Breakers

**Step Failure Circuit Breaker**:
- Threshold: 3 consecutive step failures
- Action: Abort test run immediately
- Prevents wasting resources on clearly broken tests

**Example Scenario**:
```
Step 1: Fill Username → ❌ Timeout
Step 2: Fill Password → ❌ Timeout
Step 3: Click Login → ❌ Timeout
→ Circuit breaker trips, test aborted
```

### Network Retry Backoff

**Strategy**: Exponential backoff on transient network errors

**Timing**:
1. First retry: 250ms delay
2. Second retry: 500ms delay
3. Third retry: 1000ms delay
4. Beyond: Fail fast (network likely down)

**Applicable Errors**:
- Connection timeouts
- DNS resolution failures
- HTTP 502/503/504 (Bad Gateway, Service Unavailable, Gateway Timeout)

---

## Addendum G: Flake Management

### Quarantine System

**Unstable Test Handling**:
- Label: `quarantine` applied to flaky test specs
- Exclusion: Quarantined tests excluded from merge gate
- Review: Weekly triage to fix or remove quarantined tests

**Quarantine Criteria**:
- Test fails >2 times in 10 consecutive runs
- Flake rate >10% over 30-day period

### Golden Run Snapshots

**Purpose**: Baseline for detecting selector drift

**Refresh Schedule**: Weekly (every Monday 2am UTC)
- Capture selectors used in successful test runs
- Record timing baselines (p50, p95)
- Store screenshots as visual regression baseline

**Storage**:
```
golden_runs/
  2025-11-04/
    wikipedia_search.json       # Selectors + timings
    wikipedia_search_step1.png  # Screenshot evidence
    wikipedia_search_step2.png
```

### Auto-Retry Policy

**Single Retry Allowed**: Only for `networkidle` timeouts
- Rationale: Network timing is inherently flaky
- Other failures indicate genuine bugs (don't mask with retries)

**Retry Logic**:
```python
if error.type == "TimeoutError" and "networkidle" in error.message:
    logger.warning(f"[RETRY] Network timeout on {step.element}, retrying once...")
    await asyncio.sleep(1)
    result = await retry_step(step)
```

**Prohibited Retries**:
- Element not found (selector issue, not flake)
- Gate validation failures (real problem)
- Assertion failures (test logic issue)

### Drift Canary Tests

**Nightly Execution**: Runs at 3am UTC daily

**Canary Sites**:
1. Amazon product search
2. eBay product search
3. Salesforce Accounts list view
4. Salesforce Contacts list view

**Purpose**: Early detection of UI changes before production tests fail

**Alert Threshold**:
- If canary fails 2 nights in a row → Notify team
- If all canaries fail → Incident alert (possible PACTS regression)

---

## Addendum H: CI/CD Pipeline Lanes

### PR Lane (Smoke Tests)

**Trigger**: Every pull request
**Time Budget**: ≤ 5 minutes total
**Test Suite**:
- Wikipedia article search
- GitHub repository search
- Amazon product search
- Salesforce Lightning mini-flow (login only, no opportunity creation)

**Acceptance Criteria**:
- All 4 tests must pass
- 0 heal rounds allowed
- Total duration ≤ 300 seconds

### Nightly Lane (Regression)

**Trigger**: Scheduled (3am UTC daily)
**Time Budget**: ≤ 30 minutes
**Test Suite**:
- Full enterprise test suite
- All production sites (6/6)
- Complex multi-step workflows
- Salesforce Lightning full opportunity creation

**Artifacts Generated**:
1. `run.jsonl` - Structured execution log
2. `steps.jsonl` - Per-step execution details
3. `screenshots/` - Visual evidence for each step
4. `traces/` - LangSmith distributed traces
5. `verdict.html` - Human-readable evidence pack

### MCP Safety Guardrail

**Hard Fail Condition**: MCP actions enabled without WebSocket attachment

**Rationale**:
- MCP actions mode requires live WebSocket connection to browser
- Discovery-only mode is safe (read-only operations)
- Actions without WS = guaranteed failures, waste CI resources

**Check Logic**:
```python
if MCP_ACTIONS_ENABLED and not PLAYWRIGHT_WS_ENDPOINT:
    raise ConfigError("MCP actions require PLAYWRIGHT_WS_ENDPOINT")
```

**Allowed Configuration**:
- ✅ MCP discovery-only (no WS needed)
- ✅ MCP actions + WS endpoint provided
- ❌ MCP actions without WS endpoint

---

## Addendum I: App Helper Interface (RFC Template)

### Contract Requirements

Every app-specific helper module must implement:

**1. Resolver Function**:
```python
async def resolve(target: str, within: str, context: dict) -> List[Candidate]:
    """Find all possible elements matching target within region.

    Args:
        target: Element name (e.g., "Save button", "Stage dropdown")
        within: Region scope (e.g., "App Launcher", "Modal dialog")
        context: Additional context (page, browser, step metadata)

    Returns:
        List of Candidate objects with selector + confidence score
    """
```

**2. Action Function**:
```python
async def act(page, candidate: Candidate, action: str, value: str) -> ExecResult:
    """Execute action on discovered element.

    Args:
        page: Playwright page object
        candidate: Selected element from resolve()
        action: Action type (click, fill, select, etc.)
        value: Value for fill/select actions (optional)

    Returns:
        ExecResult with success/failure + diagnostics
    """
```

**3. Required Capabilities**:
- **SPA Waits**: Must handle async page loads
- **Verification Hook**: Validate action success before returning
- **Diagnostics**: Provide debugging info on failure

### Submission Requirements

**RFC Template** for new app helpers:

1. **Problem Statement**:
   - Which enterprise app?
   - What specific UI patterns require custom handling?
   - Why don't standard discovery strategies work?

2. **Sample Pages**:
   - URLs or screenshots demonstrating the problem
   - DOM structure examples
   - Current failure modes

3. **Fallback Order**:
   - Priority sequence for discovery strategies
   - When to use type-ahead vs. DOM queries
   - When to fall back to keyboard navigation

4. **Gate Logic**:
   - Custom validation beyond five-point gate
   - App-specific element state checks
   - Success verification criteria

5. **Test Coverage**:
   - Unit tests for resolver + action functions
   - Integration test with live app
   - Edge cases (overlays, dynamic content, etc.)

### SLA Requirements

**Uniqueness**: Selectors must be unique within specified region
- No ambiguous matches
- If multiple matches, return all with confidence scores

**Performance**: p95 ≤ 2.5 seconds
- Includes all discovery attempts + fallbacks
- Measure from resolve() call to return

**Reliability**: 0 heal rounds on happy path
- Primary strategy should work >95% of time
- Fallbacks handle edge cases

**Example**: Salesforce Lightning helper meets all SLAs
- Type-ahead works >95% → 0 heal rounds
- Falls back to aria-controls, then keyboard nav
- p95 execution: 1.8 seconds

---

## Addendum J: Risk Register

### Current Risks & Mitigations

**Risk 1: MCP Re-introduction Complexity**

**Threat**: Re-enabling MCP actions mode could introduce instability
**Impact**: High (could break all tests)
**Probability**: Medium

**Mitigation**:
- Keep MCP actions disabled by default
- Enable only after effects verified in isolated environment
- Owner: Claude Code integration team

**Status**: Monitored

---

**Risk 2: Lightning Component Variance**

**Threat**: Salesforce Lightning components render differently across orgs/versions
**Impact**: Medium (Salesforce tests could fail)
**Probability**: Medium

**Mitigation**:
- Maintain dual-role matchers (role + aria-label)
- Keep keyboard navigation as rock-solid fallback
- Test across multiple Salesforce org types (Developer, Enterprise, Unlimited)
- Owner: Salesforce helper maintainer

**Status**: Active mitigation

---

**Risk 3: Network Slowness**

**Threat**: Slow networks cause discovery timeouts
**Impact**: Medium (false negatives, flaky tests)
**Probability**: Low (mostly affects remote CI)

**Mitigation**:
- Enforce `domcontentloaded` wait before discovery
- Add 1-second settle time for async SPAs
- Exponential backoff on network timeouts
- Owner: Executor agent owner

**Status**: Mitigated (implemented in v2.1)

---

**Risk 4: Vendor UI Shifts**

**Threat**: Amazon, eBay, Salesforce change UIs without notice
**Impact**: High (production tests fail)
**Probability**: Medium (happens quarterly)

**Mitigation**:
- Nightly drift canary tests
- Selector memory with 7-day TTL (invalidate stale selectors)
- Golden run snapshots for baseline comparison
- Owner: QA lead

**Status**: Active monitoring

---

## Addendum K: Operations Runbook (1-Page Reference)

### Feature Flags

**Environment Variables**:
- `USE_MCP`: Enable MCP integration (default: `false`)
- `MCP_ACTIONS_ENABLED`: Allow MCP to execute actions (default: `false`)
- `PLAYWRIGHT_WS_ENDPOINT`: WebSocket URL for MCP connection (default: `null`)

**Recommended Settings**:
- **Local development**: `USE_MCP=false` (use local Playwright)
- **CI environment**: `USE_MCP=false` (deterministic, faster)
- **MCP testing**: `USE_MCP=true`, `MCP_ACTIONS_ENABLED=false` (discovery only)

### Common Failures & Fixes

**Symptom**: `NOT_UNIQUE` error in App Launcher navigation

**Root Cause**: Multiple elements with same name, discovery not scoped to region

**Fix**:
```python
# Ensure within="App Launcher" specified in test step
step = {
    "element": "Opportunities",
    "action": "click",
    "within": "App Launcher"  # ← CRITICAL
}
```

---

**Symptom**: 2FA authentication required, test stuck waiting

**Root Cause**: Session expired, no valid cookies

**Fix**:
1. Use session reuse feature (load `hitl/salesforce_auth.json`)
2. Or run HITL flow once: `python -m backend.cli.main test --req salesforce_opportunity_hitl --headed`
3. Complete 2FA manually when prompted
4. Session saved automatically for subsequent runs

---

**Symptom**: Slow page load, discovery timeouts

**Root Cause**: SPA not finished rendering before discovery attempts

**Fix**:
- Verify page load wait is enabled (should be automatic in v2.1+)
- Increase settle time if needed: `DISCOVERY_SETTLE_MS=2000`
- Check `backend/runtime/discovery.py` for wait implementation

---

### Recovery Procedure

**When test fails unexpectedly**:

1. **Re-run with full diagnostics**:
   ```bash
   python -m backend.cli.main test --req <req_name> --headed --trace on
   ```

2. **Attach evidence pack**:
   - Screenshots: `screenshots/<req_name>_step*.png`
   - Trace files: `traces/<req_name>.json`
   - Execution logs: `logs/runs/<req_name>.jsonl`

3. **Create GitHub issue** with:
   - Test specification file
   - Full error message
   - Evidence pack (screenshots + traces)
   - Environment details (OS, Python version, Playwright version)

---

## Addendum L: Minimal Database Schema (Runs & Steps)

### Tables

**Purpose**: Persist test execution history for analysis and debugging

**Schema**:

```sql
-- Runs table: High-level test execution metadata
CREATE TABLE runs (
    id SERIAL PRIMARY KEY,
    suite VARCHAR(200) NOT NULL,           -- Test suite name
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    status VARCHAR(20),                     -- running, completed, failed
    pass_rate DECIMAL(5,2),                -- Percentage of passed steps
    slo_ok BOOLEAN,                        -- Met SLA requirements?
    artifact_uri TEXT,                     -- Path to evidence pack

    INDEX idx_started_at (started_at DESC),
    INDEX idx_suite (suite)
);

-- Run steps table: Detailed step-by-step execution log
CREATE TABLE run_steps (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES runs(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,                  -- Step index (0-based)
    action VARCHAR(50) NOT NULL,           -- click, fill, select, etc.
    target VARCHAR(200) NOT NULL,          -- Element name
    within VARCHAR(200),                   -- Region scope (optional)
    engine VARCHAR(20),                    -- local_playwright | mcp
    gates_json JSONB,                      -- Five-point gate results
    retries INTEGER DEFAULT 0,
    duration_ms INTEGER,
    status VARCHAR(20),                    -- success, failed
    screenshot_uri TEXT,

    INDEX idx_run_id_idx (run_id, idx)
);
```

### Daily Queries

**1. Yesterday's Success Rate by Suite**:
```sql
SELECT
    suite,
    COUNT(*) as total_runs,
    AVG(pass_rate) as avg_pass_rate,
    COUNT(*) FILTER (WHERE slo_ok = true) as slo_compliant
FROM runs
WHERE started_at >= CURRENT_DATE - INTERVAL '1 day'
  AND started_at < CURRENT_DATE
GROUP BY suite
ORDER BY suite;
```

**2. Top 10 Slowest Steps**:
```sql
SELECT
    target,
    action,
    within,
    AVG(duration_ms) as avg_duration_ms,
    COUNT(*) as execution_count
FROM run_steps
WHERE status = 'success'
  AND executed_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY target, action, within
ORDER BY avg_duration_ms DESC
LIMIT 10;
```

**3. Flake Offenders (Most Retries)**:
```sql
SELECT
    target,
    action,
    COUNT(*) as failure_count,
    AVG(retries) as avg_retries
FROM run_steps
WHERE retries > 0
  AND executed_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY target, action
ORDER BY avg_retries DESC, failure_count DESC
LIMIT 10;
```

---

## Addendum M: Success Tokens Registry (Per App/Page)

### Purpose

Define success verification criteria for each supported application to validate navigation and action completion.

### Salesforce Lightning

**Opportunity Created**:
- Toast message contains: `"was created"`
- URL pattern: `/lightning/r/Opportunity/<record_id>/view`
- Page element visible: `role=heading` containing opportunity name

**Account Created**:
- Toast message contains: `"was saved"`
- URL pattern: `/lightning/r/Account/<record_id>/view`

**General Navigation Success**:
- URL contains: `/lightning/o/` (object list) or `/lightning/r/` (record view)
- Lightning spinner not visible: `[class*="spinner"]` has count = 0

### Wikipedia

**Article Loaded**:
- URL pattern: `**/wiki/**` (indicates article page)
- Page heading visible: `role=heading` with article title

**Search Successful**:
- Search results container visible: `#mw-content-text`
- At least one result link: `.mw-search-result` count > 0

### Amazon

**Search Results Loaded**:
- Results container visible: `[data-component-type="s-search-results"]`
- Results summary text contains: `"results for"`
- Product count indicator: `span.s-result-count` visible

**Product Page Loaded**:
- Product title visible: `#productTitle`
- Add to cart button: `#add-to-cart-button` enabled

### GitHub

**Search Results Loaded**:
- URL pattern: `**/search?**`
- Results count indicator visible: `.codesearch-results h3`
- At least one result: `.repo-list-item` count > 0

**Repository Page Loaded**:
- Repository name visible: `[itemprop="name"]`
- Clone button visible: `button[data-target="get-repo.cloneButton"]`

### Usage

Success tokens should be checked after navigation or action completion to verify the operation succeeded. Example:

```python
# After clicking "Save" on Salesforce Opportunity
await page.wait_for_url_pattern("/lightning/r/Opportunity/*/view", timeout=5000)
toast = await page.get_by_text("was created").is_visible()
if not toast:
    raise AssertionError("Success token not found: toast message")
```

---

**Document Version**: 2.1.1 (with addenda)
**Last Updated**: 2025-11-02
**Status**: Living document - update as features implemented
