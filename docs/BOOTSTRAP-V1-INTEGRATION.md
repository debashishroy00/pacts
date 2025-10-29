# PACTS Bootstrap v1 Integration

**Date**: October 28, 2025
**Status**: ✅ DELIVERED
**Source**: pacts-backend-bootstrap-v1.zip

---

## What Was Delivered

### 🎯 Core Components

#### 1. LangGraph State Machine (`backend/graph/`)

**`state.py`** - State definitions
- `RunState` (Pydantic model) - Complete state schema
- `Failure` enum - Failure types (none, not_unique, not_visible, disabled, unstable, timeout)
- Helper functions for state management

**`build_graph.py`** - Graph construction
- `StateGraph(RunState)` initialization
- Entry point: `planner`
- Basic flow: `planner → END`
- `ainvoke_graph()` async function for execution
- Ready for expansion to 6-agent pipeline

#### 2. Planner Agent (`backend/agents/planner.py`)

**Features:**
- ✅ `parse_steps()` function - Parses intent format: `"Element@Region | action | value"`
- ✅ `@traced("planner")` decorator - LangSmith integration
- ✅ `async run(state: RunState)` - Async agent execution
- ✅ Extracts intents from raw steps
- ✅ Updates state context with parsed intents

**Intent Format Supported:**
```
"SearchInput@Header | fill | playwright"
"SearchButton@Header | click"
"LoginForm@Main | fill | username"
```

**Output:**
```python
{
  "intent": "SearchInput@Header",
  "element": "SearchInput",
  "region": "Header",
  "action": "fill",
  "value": "playwright"
}
```

#### 3. Telemetry (`backend/telemetry/tracing.py`)

**Features:**
- ✅ `@traced()` async context manager
- ✅ LangSmith integration stub
- ✅ Ready for production telemetry
- ✅ Span creation and logging

#### 4. FastAPI Server (`backend/api/main.py`)

**Endpoints:**
- ✅ `GET /health` - Health check endpoint
- ✅ CORS middleware configured
- ✅ Ready for additional routes

#### 5. CLI Interface (`backend/cli/main.py`)

**Features:**
- ✅ Run planner via command line
- ✅ Arguments: `--req`, `--url`, `--steps`
- ✅ JSON output to stdout
- ✅ Pretty-printed results

**Usage:**
```bash
python -m backend.cli.main \
  --req REQ-1 \
  --url https://example.com \
  --steps "SearchInput@Header|fill|q" "SearchButton@Header|click"
```

#### 6. Unit Tests (`backend/tests/unit/test_planner.py`)

**Coverage:**
- ✅ Test `parse_steps()` function
- ✅ Validate intent parsing
- ✅ Test with multiple step formats
- ✅ Edge case handling
- ✅ pytest async support

---

## File Structure

```
backend/
├── graph/
│   ├── __init__.py
│   ├── state.py              ✅ RunState, Failure enum
│   └── build_graph.py        ✅ LangGraph setup
│
├── agents/
│   ├── __init__.py
│   └── planner.py            ✅ Planner agent (complete)
│
├── telemetry/
│   ├── __init__.py
│   └── tracing.py            ✅ LangSmith tracing
│
├── api/
│   ├── __init__.py
│   └── main.py               ✅ FastAPI /health
│
├── cli/
│   ├── __init__.py
│   └── main.py               ✅ CLI interface
│
└── tests/
    └── unit/
        └── test_planner.py   ✅ Unit tests
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Run Planner via CLI

```bash
python -m backend.cli.main \
  --req REQ-001 \
  --url https://www.saucedemo.com \
  --steps "UsernameInput@LoginForm|fill|standard_user" \
         "PasswordInput@LoginForm|fill|secret_sauce" \
         "LoginButton@LoginForm|click"
```

**Expected Output:**
```json
{
  "req_id": "REQ-001",
  "step_idx": 0,
  "heal_round": 0,
  "context": {
    "url": "https://www.saucedemo.com",
    "intents": [
      {
        "intent": "UsernameInput@LoginForm",
        "element": "UsernameInput",
        "region": "LoginForm",
        "action": "fill",
        "value": "standard_user"
      },
      {
        "intent": "PasswordInput@LoginForm",
        "element": "PasswordInput",
        "region": "LoginForm",
        "action": "fill",
        "value": "secret_sauce"
      },
      {
        "intent": "LoginButton@LoginForm",
        "element": "LoginButton",
        "region": "LoginForm",
        "action": "click",
        "value": null
      }
    ]
  },
  "failure": "none"
}
```

### 3. Run Unit Tests

```bash
pytest backend/tests/unit/test_planner.py -v
```

**Expected:**
```
test_planner.py::test_parse_steps PASSED
test_planner.py::test_parse_steps_minimal PASSED
test_planner.py::test_parse_steps_edge_cases PASSED
```

### 4. Start FastAPI Server

```bash
cd backend
uvicorn api.main:app --reload
```

**Access:**
- Health: http://localhost:8000/health
- Swagger: http://localhost:8000/docs

---

## Next Steps (Suggested Sequence)

### 🎯 Move 1: Run Planner CLI (DONE ✅)

**Status**: Delivered in bootstrap
**Action**: Test the CLI to verify it works

### 🎯 Move 2: Implement POMBuilder Agent (NEXT - CRITICAL)

**Priority**: HIGH - Most complex agent
**Estimate**: 7-10 days

**Tasks:**
1. Create `backend/runtime/browser_client.py`
   - Async Playwright wrapper
   - `start()`, `goto()`, `query()`, `visible()`, `enabled()`, `bbox_stable()`

2. Create `backend/runtime/browser_manager.py`
   - Singleton pattern
   - Lifecycle management

3. Create `backend/runtime/discovery.py`
   - Multi-strategy selector discovery:
     - ✅ Semantic (role, label, text)
     - ✅ Shadow DOM piercing
     - ✅ Iframe traversal (optional for v1)
     - ✅ Pattern extraction (optional for v1)
     - ⏭️ Vision (Phase 2)
   - Returns ranked candidates with confidence scores

4. Create `backend/runtime/policies.py`
   - 5-point actionability gate:
     - Unique (count == 1)
     - Visible (is_visible)
     - Enabled (is_enabled)
     - Stable (bbox_stable)
     - Scoped (not covered)

5. Create `backend/agents/pom_builder.py`
   - `async run(state: RunState)`
   - Navigate to URL
   - For each intent, discover selector
   - Validate through 5-point gate
   - Build fallback chains
   - Update `context["plan"]` with verified selectors

6. Update `backend/graph/build_graph.py`
   - Add `pom_builder` node
   - Add edge: `planner → pom_builder`

7. Create `backend/tests/unit/test_pom_builder.py`

**Acceptance Criteria:**
- ✅ Discovers selectors for 90%+ of intents on SauceDemo
- ✅ 5-point gate passes for discovered selectors
- ✅ Generates fallback chains with confidence scores
- ✅ Unit tests pass

---

### 🎯 Move 3: Extend Graph for Full Pipeline

**Priority**: MEDIUM
**Estimate**: 5-7 days

**Tasks:**
1. Create remaining agents:
   - `backend/agents/generator.py`
   - `backend/agents/executor.py`
   - `backend/agents/oracle_healer.py`
   - `backend/agents/verdict_rca.py`

2. Update `backend/graph/build_graph.py`:
   ```python
   g.add_node("planner", planner.run)
   g.add_node("pom_builder", pom_builder.run)
   g.add_node("generator", generator.run)
   g.add_node("executor", executor.run)
   g.add_node("oracle_healer", oracle_healer.run)
   g.add_node("verdict_rca", verdict_rca.run)

   g.set_entry_point("planner")
   g.add_edge("planner", "pom_builder")
   g.add_edge("pom_builder", "generator")
   g.add_edge("generator", "executor")
   g.add_conditional_edges("executor", route_after_execute, ...)
   g.add_conditional_edges("oracle_healer", route_after_heal, ...)
   ```

3. Wire verdict API:
   - `backend/api/routes/verdicts.py`
   - `GET /api/verdicts/{req_id}`
   - `GET /api/verdicts/{req_id}/metrics`
   - `GET /api/verdicts/{req_id}/rca`

4. Create E2E test:
   - `backend/tests/e2e/test_full_pipeline.py`
   - Run complete flow: REQ → Verdict

**Acceptance Criteria:**
- ✅ Full 6-agent pipeline executes
- ✅ Test.py files generated
- ✅ Tests execute successfully
- ✅ Verdicts stored in database
- ✅ E2E test passes

---

## Current Capabilities

### ✅ What Works Now

1. **Planner Agent**
   - Parses intent format
   - Extracts element, region, action, value
   - Updates LangGraph state
   - CLI execution
   - Unit tested

2. **LangGraph State Machine**
   - RunState schema defined
   - Failure enum
   - Basic graph structure
   - Async invocation

3. **Telemetry**
   - LangSmith tracing decorator
   - Ready for production

4. **API & CLI**
   - Health endpoint
   - CLI interface
   - JSON output

### ⏭️ What's Missing

1. **POMBuilder Agent** (CRITICAL NEXT)
2. **Generator Agent**
3. **Executor Agent**
4. **OracleHealer Agent**
5. **VerdictRCA Agent**
6. **Postgres integration**
7. **Redis caching**
8. **WebSocket endpoints**

---

## Development Workflow

### Adding a New Agent

**Template:**

```python
# backend/agents/my_agent.py
from backend.graph.state import RunState, Failure
from backend.telemetry.tracing import traced

@traced("my_agent")
async def run(state: RunState) -> RunState:
    """
    My agent description.

    Input: state.context["input_key"]
    Output: state.context["output_key"]
    """
    # Agent logic here
    state.context["output_key"] = "value"
    return state
```

**Register in graph:**

```python
# backend/graph/build_graph.py
from backend.agents import my_agent

g.add_node("my_agent", my_agent.run)
g.add_edge("previous_node", "my_agent")
```

**Add unit test:**

```python
# backend/tests/unit/test_my_agent.py
import pytest
from backend.graph.state import RunState
from backend.agents.my_agent import run

@pytest.mark.asyncio
async def test_my_agent():
    state = RunState(req_id="TEST-1", context={"input_key": "value"})
    result = await run(state)
    assert result.context["output_key"] == "expected"
```

---

## Testing Strategy

### Unit Tests
- Test individual agent logic
- Mock external dependencies (Playwright, LLM, DB)
- Fast execution (<1s per test)

### Integration Tests
- Test agent interactions
- Real Playwright browser
- Real Redis/Postgres (Docker)
- Medium execution (1-5s per test)

### E2E Tests
- Full pipeline execution
- Real websites (SauceDemo, etc.)
- Complete workflow validation
- Slow execution (30s-2min per test)

**Example:**

```bash
# Fast (unit only)
pytest tests/unit/ -v

# With integration
pytest tests/unit/ tests/integration/ -v

# Full suite (slow)
pytest -v

# With coverage
pytest --cov=backend --cov-report=html
```

---

## Recommended Development Order

### Week 1: POMBuilder Foundation
1. Day 1-2: BrowserClient + BrowserManager (Playwright wrapper)
2. Day 3-4: Discovery strategies (Semantic + Shadow DOM)
3. Day 5: 5-point actionability gate
4. Day 6-7: POMBuilder agent + integration

### Week 2: Generator + Executor
1. Day 1-3: Generator agent (Jinja2 templates, test.py generation)
2. Day 4-5: Executor agent (run tests, capture evidence)
3. Day 6-7: Integration testing

### Week 3: Healing + Verdict
1. Day 1-3: OracleHealer agent (reveal, reprobe, stability wait)
2. Day 4-5: VerdictRCA agent (reporting, metrics)
3. Day 6-7: Full pipeline integration

### Week 4: APIs + Polish
1. Day 1-2: FastAPI routes (requirements, runs, verdicts)
2. Day 3-4: WebSocket for real-time updates
3. Day 5-6: E2E testing
4. Day 7: Documentation + deployment guide

---

## Success Metrics

### Phase 1 Complete When:
- ✅ All 6 agents implemented
- ✅ LangGraph pipeline executes end-to-end
- ✅ Test.py files generated successfully (90%+)
- ✅ Generated tests execute (85%+)
- ✅ Healing works (60%+ success)
- ✅ Verdicts stored in Postgres
- ✅ APIs functional
- ✅ CLI works
- ✅ E2E tests pass on SauceDemo
- ✅ Documentation complete

---

## Next Immediate Action

**RECOMMENDED: Start POMBuilder Agent**

**Why POMBuilder first?**
1. Most complex agent (7-10 days)
2. Critical for success (Find-First verification)
3. Other agents depend on its output
4. High risk - tackle early

**Steps:**
1. Create `backend/runtime/browser_client.py` (Playwright wrapper)
2. Implement semantic discovery strategy
3. Implement 5-point gate
4. Create POMBuilder agent
5. Test on SauceDemo login form

**Acceptance Test:**
```bash
# Should discover and verify username, password, login button
python -m backend.cli.main \
  --req REQ-LOGIN \
  --url https://www.saucedemo.com \
  --steps "UsernameInput@LoginForm|fill|user" \
         "PasswordInput@LoginForm|fill|pass" \
         "LoginButton@LoginForm|click"

# Expected output:
# {
#   "context": {
#     "plan": [
#       {"selector": "#user-name", "confidence": 0.95, ...},
#       {"selector": "#password", "confidence": 0.95, ...},
#       {"selector": "#login-button", "confidence": 0.95, ...}
#     ]
#   }
# }
```

---

**Status**: ✅ Bootstrap v1 integrated and documented
**Next**: 🎯 Implement POMBuilder agent (Move 2)

Ready when you are!
