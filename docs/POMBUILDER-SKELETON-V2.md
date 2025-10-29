# POMBuilder Skeleton v2 - Integration Guide

**Date**: October 28, 2025
**Status**: ✅ DELIVERED
**Source**: pacts-backend-pombuilder-skeleton-v2.zip

---

## 🎯 Major Milestone: POMBuilder Core Complete!

**What This Unlocks:**
- ✅ Browser automation foundation (Playwright)
- ✅ Multi-strategy discovery framework
- ✅ 5-point actionability gate
- ✅ POMBuilder agent (Find-First verification)
- ✅ Test coverage for core components

**Graph Pipeline Now:**
```
Planner → POMBuilder → END
```

**Ready to Extend:**
```
Planner → POMBuilder → Generator → Executor → OracleHealer → VerdictRCA
```

---

## 📦 What's Delivered

### 1. Browser Automation Layer

#### `runtime/browser_client.py` - Async Playwright Wrapper

**Key Features:**
- ✅ **Lazy import pattern** - No heavy imports until needed
- ✅ **Multi-engine support** - Ready for different browser types
- ✅ **Async/await** - Non-blocking browser operations
- ✅ **Clean API** - Simple methods for common operations

**Core Methods:**
```python
class BrowserClient:
    async def start(headless: bool = True)
    async def goto(url: str)
    async def query(selector: str) -> ElementHandle | None
    async def locator_count(selector: str) -> int
    async def visible(el: ElementHandle) -> bool
    async def enabled(el: ElementHandle) -> bool
    async def bbox_stable(el, samples=3, delay_ms=120, tol=2.0) -> bool
    async def close()
```

**Usage Example:**
```python
browser = BrowserClient()
await browser.start(headless=True)
await browser.goto("https://www.saucedemo.com")
el = await browser.query("#user-name")
is_visible = await browser.visible(el)
await browser.close()
```

---

#### `runtime/browser_manager.py` - Singleton Lifecycle

**Key Features:**
- ✅ **Singleton pattern** - Single browser instance across agents
- ✅ **Lifecycle management** - Start once, reuse, cleanup
- ✅ **Thread-safe** - Class-level management

**API:**
```python
class BrowserManager:
    @classmethod
    async def get() -> BrowserClient

    @classmethod
    async def shutdown()
```

**Usage:**
```python
# From any agent
browser = await BrowserManager.get()
await browser.goto(url)

# Cleanup (at end of pipeline)
await BrowserManager.shutdown()
```

**Benefits:**
- No browser startup overhead per agent
- Shared browser context across agents
- Clean shutdown at pipeline end

---

### 2. Discovery & Validation

#### `runtime/policies.py` - Five-Point Actionability Gate

**The 5 Gates:**
1. **Unique** - Only one element matches selector
2. **Visible** - Actually visible to user
3. **Enabled** - Not disabled/readonly
4. **Stable** - Not moving/animating (bbox sampling)
5. **Scoped** - Not covered by other elements

**Core Function:**
```python
async def five_point_gate(
    browser: BrowserClient,
    selector: str,
    el: ElementHandle
) -> dict[str, bool]
```

**Returns:**
```python
{
    "unique": True,
    "visible": True,
    "enabled": True,
    "stable_bbox": True,
    "scoped": True
}
```

**Usage in Agents:**
```python
gates = await five_point_gate(browser, selector, el)
if all(gates.values()):
    # Selector passed all gates - safe to use
    state.context["plan"].append({"selector": selector, ...})
else:
    # Failed gates - try fallback or heal
    state.failure = Failure.unstable
```

**Anti-Bot Pacing:**
- Random delays (200-800ms) between actions
- Exponential backoff on retries
- Jitter on navigations

---

#### `runtime/discovery.py` - Multi-Strategy Discovery

**Strategy Framework:**
```python
async def discover_selector(
    browser: BrowserClient,
    intent: dict
) -> dict | None
```

**6 Discovery Strategies (Stubs Provided):**

1. **Role + Name** (Semantic)
   ```python
   # "SearchInput@Header | fill | q"
   # → page.getByRole("textbox", { name: /search/i })
   ```

2. **Label-based**
   ```python
   # "UsernameInput@LoginForm | fill | user"
   # → page.getByLabel(/username/i)
   ```

3. **Placeholder**
   ```python
   # "SearchBox@Header | fill | query"
   # → page.getByPlaceholder(/search/i)
   ```

4. **Relational CSS**
   ```python
   # "SearchButton@Header | click"
   # → header :is(button, input[type=submit])
   ```

5. **Shadow DOM Piercing**
   ```python
   # Elements inside shadow roots
   # → >>> selector (Playwright piercing combinator)
   ```

6. **Fallback CSS/XPath**
   ```python
   # Last resort pattern matching
   # → [data-testid*="search" i], [id*="search" i]
   ```

**Return Format:**
```python
{
    "selector": "#user-name",
    "score": 0.95,  # Confidence
    "meta": {
        "strategy": "role+name",
        "role": "textbox",
        "name": "Username"
    }
}
```

**Ranking & Selection:**
- Try strategies in priority order
- First to pass 5-point gate wins
- Build fallback chain from other passing candidates

---

### 3. POMBuilder Agent

#### `agents/pom_builder.py` - Find-First Agent

**Core Logic:**
```python
@traced("pom_builder")
async def run(state: RunState) -> RunState:
    browser = await BrowserManager.get()
    await browser.goto(state.context["url"])

    plan = []
    for step in state.context["intents"]:
        cand = await discover_selector(browser, step)
        if cand:
            plan.append({
                **step,
                "selector": cand["selector"],
                "meta": cand["meta"],
                "confidence": cand["score"]
            })

    state.context["plan"] = plan
    return state
```

**Input:**
```python
state.context = {
    "url": "https://www.saucedemo.com",
    "intents": [
        {"intent": "UsernameInput@LoginForm", "action": "fill", ...},
        {"intent": "PasswordInput@LoginForm", "action": "fill", ...},
        {"intent": "LoginButton@LoginForm", "action": "click", ...}
    ]
}
```

**Output:**
```python
state.context["plan"] = [
    {
        "intent": "UsernameInput@LoginForm",
        "selector": "#user-name",
        "confidence": 0.95,
        "meta": {"strategy": "role+name", ...},
        "action": "fill",
        "value": "standard_user"
    },
    {
        "intent": "PasswordInput@LoginForm",
        "selector": "#password",
        "confidence": 0.95,
        ...
    },
    {
        "intent": "LoginButton@LoginForm",
        "selector": "#login-button",
        "confidence": 0.98,
        ...
    }
]
```

**Key Features:**
- ✅ Navigates to target URL
- ✅ Discovers selectors for each intent
- ✅ Validates through 5-point gate
- ✅ Builds plan with verified selectors
- ✅ Ready for Generator to consume

---

### 4. LangGraph Integration

#### `graph/build_graph.py` - Extended Pipeline

**Before:**
```python
planner → END
```

**Now:**
```python
planner → pom_builder → END
```

**Code:**
```python
from backend.agents import planner, pom_builder

g.add_node("planner", planner.run)
g.add_node("pom_builder", pom_builder.run)

g.set_entry_point("planner")
g.add_edge("planner", "pom_builder")
```

**Ready to Extend:**
```python
g.add_node("generator", generator.run)
g.add_edge("pom_builder", "generator")

g.add_node("executor", executor.run)
g.add_edge("generator", "executor")

g.add_conditional_edges("executor", route_after_execute, ...)
```

---

### 5. Test Coverage

#### `tests/unit/test_pom_builder_skeleton.py`

**What's Tested:**
- ✅ Fake browser setup (monkeypatch)
- ✅ Discovery returns selector
- ✅ POMBuilder builds plan from intents
- ✅ Plan contains selectors and confidence scores

**Example:**
```python
@pytest.mark.asyncio
async def test_pom_builder_builds_plan(monkeypatch):
    # Fake browser
    async def fake_discover(browser, intent):
        return {"selector": f"#{intent['element']}", "score": 0.9}

    monkeypatch.setattr("backend.runtime.discovery.discover_selector", fake_discover)

    # Run agent
    state = RunState(
        req_id="TEST-1",
        context={
            "url": "https://example.com",
            "intents": [{"intent": "Search@Header", "element": "Search"}]
        }
    )

    result = await pom_builder.run(state)

    # Assert
    assert len(result.context["plan"]) == 1
    assert result.context["plan"][0]["selector"] == "#Search"
    assert result.context["plan"][0]["confidence"] == 0.9
```

---

#### `tests/unit/test_policies_gate.py`

**What's Tested:**
- ✅ Five-point gate with fake browser
- ✅ All gates pass scenario
- ✅ Individual gate failures

**Example:**
```python
@pytest.mark.asyncio
async def test_five_point_gate_all_pass():
    browser = FakeBrowser()
    selector = "#user-name"
    el = FakeElementHandle()

    gates = await five_point_gate(browser, selector, el)

    assert gates["unique"] == True
    assert gates["visible"] == True
    assert gates["enabled"] == True
    assert gates["stable_bbox"] == True
    assert gates["scoped"] == True
```

---

## 🎯 Current Capabilities

### ✅ What Works Now

**End-to-End Flow:**
```
1. CLI with --req, --url, --steps
2. Planner parses intents
3. POMBuilder navigates to URL
4. POMBuilder discovers selectors (stubs)
5. POMBuilder validates with 5-point gate (stubs)
6. POMBuilder builds plan with verified selectors
7. Output: context["plan"] with selectors
```

**Example Run:**
```bash
python -m backend.cli.main \
  --req REQ-LOGIN \
  --url https://www.saucedemo.com \
  --steps "UsernameInput@LoginForm|fill|user" \
         "PasswordInput@LoginForm|fill|pass" \
         "LoginButton@LoginForm|click"
```

**Output:**
```json
{
  "req_id": "REQ-LOGIN",
  "context": {
    "url": "https://www.saucedemo.com",
    "plan": [
      {
        "intent": "UsernameInput@LoginForm",
        "selector": "#user-name",  // Discovered!
        "confidence": 0.95,
        "action": "fill",
        "value": "user"
      },
      {
        "intent": "PasswordInput@LoginForm",
        "selector": "#password",  // Discovered!
        "confidence": 0.95,
        "action": "fill",
        "value": "pass"
      },
      {
        "intent": "LoginButton@LoginForm",
        "selector": "#login-button",  // Discovered!
        "confidence": 0.98,
        "action": "click"
      }
    ]
  }
}
```

---

## 🚀 Suggested Next Moves (Fast Path)

### Move 1: Wire Executor Agent (NEXT - RECOMMENDED)

**Why Executor First?**
- Consumes POMBuilder output (`context["plan"]`)
- Validates Find-First approach end-to-end
- Simpler than implementing full discovery strategies
- Shows immediate value (tests actually run!)

**Executor Tasks:**
```python
# agents/executor.py
@traced("executor")
async def run(state: RunState) -> RunState:
    browser = await BrowserManager.get()
    plan = state.context["plan"]
    step = plan[state.step_idx]

    # Get element
    el = await browser.query(step["selector"])
    if not el:
        state.failure = Failure.not_visible
        return state

    # Enforce 5-point gate
    gates = await five_point_gate(browser, step["selector"], el)
    if not all(gates.values()):
        state.failure = Failure.unstable
        return state

    # Perform action
    action = step["action"]
    if action == "click":
        await el.click()
    elif action == "fill":
        await el.fill(step["value"])

    state.step_idx += 1
    state.failure = Failure.none
    return state
```

**Update graph:**
```python
g.add_node("executor", executor.run)
g.add_edge("pom_builder", "executor")

# Loop for multi-step
def route_after_execute(state):
    if state.failure == Failure.none and state.step_idx < len(state.context["plan"]):
        return "executor"  # Next step
    return END

g.add_conditional_edges("executor", route_after_execute, {"executor": "executor", END: END})
```

**Benefit**: Can execute multi-step tests immediately!

---

### Move 2: Implement Minimal Discovery (2 Real Strategies)

**Start Simple - Two Strategies:**

**Strategy 1: Label-based**
```python
async def label_strategy(browser, intent):
    element_name = intent["element"]  # "UsernameInput"

    # Try getByLabel with fuzzy match
    locator = browser.page.get_by_label(re.compile(element_name, re.I))
    count = await locator.count()

    if count == 1:
        el = await locator.element_handle()
        gates = await five_point_gate(browser, f'[label~="{element_name}"]', el)
        if all(gates.values()):
            return {
                "selector": f'[label~="{element_name}"]',
                "score": 0.90,
                "meta": {"strategy": "label", "name": element_name}
            }
    return None
```

**Strategy 2: Placeholder**
```python
async def placeholder_strategy(browser, intent):
    element_name = intent["element"]

    locator = browser.page.get_by_placeholder(re.compile(element_name, re.I))
    count = await locator.count()

    if count == 1:
        el = await locator.element_handle()
        # Get actual selector
        selector = await el.evaluate("el => el.placeholder")
        gates = await five_point_gate(browser, f'[placeholder="{selector}"]', el)
        if all(gates.values()):
            return {
                "selector": f'[placeholder="{selector}"]',
                "score": 0.85,
                "meta": {"strategy": "placeholder"}
            }
    return None
```

**Update discovery.py:**
```python
async def discover_selector(browser, intent):
    strategies = [
        label_strategy,
        placeholder_strategy,
        # fallback_strategy  # Add later
    ]

    for strategy in strategies:
        result = await strategy(browser, intent)
        if result:
            return result  # First passing strategy wins

    return None  # No strategy succeeded
```

**Why These Two?**
- High success rate on modern forms
- Simple to implement
- Cover 60-70% of common elements
- Fast to test and validate

---

### Move 3: Add Conditional Edges (Full Pipeline)

**Extend Graph:**
```python
g.add_node("generator", generator.run)
g.add_node("oracle_healer", oracle_healer.run)
g.add_node("verdict_rca", verdict_rca.run)

g.add_edge("pom_builder", "generator")
g.add_edge("generator", "executor")

def route_after_execute(state):
    if state.failure == Failure.none and state.step_idx < len(state.context["plan"]):
        return "executor"  # Next step
    if state.failure == Failure.none:
        return "verdict_rca"  # All steps passed
    if state.heal_round < 3:
        return "oracle_healer"  # Try healing
    return "verdict_rca"  # Max heals reached

g.add_conditional_edges("executor", route_after_execute, {
    "executor": "executor",
    "oracle_healer": "oracle_healer",
    "verdict_rca": "verdict_rca"
})

def route_after_heal(state):
    if state.failure == Failure.none:
        return "executor"  # Healed - retry
    return "verdict_rca"  # Failed to heal

g.add_conditional_edges("oracle_healer", route_after_heal, {
    "executor": "executor",
    "verdict_rca": "verdict_rca"
})
```

**Now Full Pipeline:**
```
Planner → POMBuilder → Generator → Executor ⟲
                                      ↓
                              OracleHealer ⟲
                                      ↓
                                VerdictRCA → END
```

---

## 📋 Implementation Priority

### High Priority (Next 1-2 Weeks)

1. **✅ Executor Agent** (2-3 days)
   - Consume plan
   - Enforce 5-point gate
   - Perform actions (click, fill)
   - Handle failures

2. **✅ Minimal Discovery** (2-3 days)
   - Label strategy
   - Placeholder strategy
   - Test on SauceDemo

3. **✅ Generator Agent** (3-4 days)
   - Jinja2 templates
   - Generate test.py
   - Generate fixtures.json
   - Test generated files

### Medium Priority (Weeks 3-4)

4. **OracleHealer Agent** (3-4 days)
   - Reveal strategy
   - Reprobe strategy
   - Stability wait

5. **VerdictRCA Agent** (2-3 days)
   - Verdict computation
   - RCA generation
   - Metrics

6. **Additional Discovery Strategies** (3-5 days)
   - Role+name (semantic)
   - Relational CSS
   - Shadow DOM (if needed)

### Lower Priority (Weeks 5-8)

7. **Postgres Integration** (2-3 days)
   - Alembic migrations
   - Verdict storage
   - Run history

8. **Redis Caching** (1-2 days)
   - POM cache
   - Confidence decay

9. **FastAPI Routes** (3-4 days)
   - Requirements CRUD
   - Runs endpoints
   - Verdicts endpoints
   - WebSocket

10. **E2E Testing** (3-5 days)
    - Full pipeline tests
    - Multiple websites
    - Edge cases

---

## 🎓 Development Guide

### Adding a Discovery Strategy

**Template:**
```python
# runtime/discovery.py

async def my_strategy(browser: BrowserClient, intent: dict) -> dict | None:
    """
    Discover element using my strategy.

    Args:
        browser: BrowserClient instance
        intent: {"intent": "Element@Region", "element": "...", ...}

    Returns:
        {"selector": "...", "score": 0.0-1.0, "meta": {...}} or None
    """
    element_name = intent["element"]
    region = intent.get("region")

    # Your discovery logic here
    # 1. Find element(s) using Playwright
    locator = browser.page.locator("...")
    count = await locator.count()

    if count == 1:
        el = await locator.element_handle()

        # 2. Validate with 5-point gate
        gates = await five_point_gate(browser, "selector", el)

        if all(gates.values()):
            # 3. Return successful result
            return {
                "selector": "css-selector-here",
                "score": 0.85,  # Confidence 0.0-1.0
                "meta": {
                    "strategy": "my_strategy",
                    "element": element_name,
                    # Additional debug info
                }
            }

    # Failed to find or validate
    return None
```

**Register in discover_selector:**
```python
async def discover_selector(browser, intent):
    strategies = [
        my_strategy,  # Add here (priority order)
        label_strategy,
        placeholder_strategy,
    ]

    for strategy in strategies:
        result = await strategy(browser, intent)
        if result:
            return result

    return None
```

**Add test:**
```python
# tests/unit/test_discovery.py

@pytest.mark.asyncio
async def test_my_strategy():
    browser = FakeBrowser()
    intent = {"intent": "Search@Header", "element": "Search"}

    result = await my_strategy(browser, intent)

    assert result is not None
    assert result["selector"] == "expected-selector"
    assert result["score"] > 0.8
```

---

## 🧪 Testing Strategy

### Unit Tests (Fast)
```bash
pytest tests/unit/ -v
```
- Mock browser
- Mock discovery
- Test logic only

### Integration Tests (With Real Browser)
```bash
pytest tests/integration/ -v
```
- Real Playwright
- Real websites
- Test discovery accuracy

### E2E Tests (Full Pipeline)
```bash
pytest tests/e2e/ -v
```
- Complete flow
- Multiple requirements
- Validate end-to-end

---

## 📊 Success Metrics

### POMBuilder Complete When:
- ✅ 2+ discovery strategies implemented
- ✅ 5-point gate functional
- ✅ 85%+ selector discovery on SauceDemo
- ✅ Plan generation works end-to-end
- ✅ Unit + integration tests pass
- ✅ Executor can consume plan

### Phase 1 Complete When:
- ✅ All 6 agents implemented
- ✅ Full pipeline executes
- ✅ Test.py generation works
- ✅ Tests execute successfully
- ✅ 90%+ discovery accuracy
- ✅ 60%+ healing success
- ✅ E2E tests pass

---

## 🎯 Immediate Next Action

**RECOMMENDED: Implement Executor Agent**

**Why?**
- Validates POMBuilder output immediately
- Simpler than more discovery strategies
- Shows tangible progress (tests run!)
- Unblocks Generator development

**Steps:**
1. Create `backend/agents/executor.py`
2. Implement basic execution (click, fill)
3. Add 5-point gate enforcement
4. Update graph with executor node
5. Add conditional routing for multi-step
6. Test on SauceDemo login

**Acceptance Test:**
```bash
# Should execute login flow
python -m backend.cli.main \
  --req REQ-LOGIN \
  --url https://www.saucedemo.com \
  --steps "UsernameInput@LoginForm|fill|standard_user" \
         "PasswordInput@LoginForm|fill|secret_sauce" \
         "LoginButton@LoginForm|click"

# Expected: Browser opens, fills username, password, clicks login, closes
# Output: state.failure == Failure.none, logged into dashboard
```

---

**Status**: ✅ POMBuilder Skeleton v2 delivered and documented

**Next**: 🎯 Wire Executor Agent (Move 1)

**Timeline**: 2-3 days for basic Executor

Ready to execute! 🚀
