
# PACTS-Build-Blueprint-v3.3

Status: FINAL (Claude-ready) • Language: **Python only** • Target: MVP in 1–2 weeks

## 0) Why this blueprint
Production-ready design for **PACTS** (Playwright Agents Autonomous Context Testing System) using **LangGraph 1.0 GA** for deterministic orchestration, **Playwright** for runtime, **LangSmith** for observability, and **Postgres/Redis** for state + memory. Optimized for: **reliability, self-healing, and requirement-driven testing** (RDT).

---

## 1) Stack & Versions (Pinned)
- python: 3.11+
- langgraph: `>=1.0.0,<2.0.0`
- langchain: `>=0.3.0,<0.4.0`
- playwright: `>=1.45,<2.0`
- tenacity: `>=8.2,<9.0`
- pydantic: `>=2.6,<3.0`
- psycopg[binary]: `>=3.2,<4.0`
- redis: `>=5.0,<6.0`
- openpyxl: `>=3.1,<4.0`
- langsmith: `>=0.1.39`
- alembic: `>=1.13,<2.0`
- uvloop (linux/mac), python-dotenv

> MVP decision: **Direct Playwright** (async) first. MCP bridge optional later.

---

## 2) Repository Layout

```
pacts/
├─ graph/                 # LangGraph orchestration
│  ├─ state.py            # RunState, enums, dataclasses
│  ├─ build_graph.py      # nodes + edges + checkpointer
│  └─ nodes/              # node adapters (thin)
├─ agents/                # 5 agents
│  ├─ planner.py          # parse REQ → intents + oracles
│  ├─ pom_builder.py      # Find-First discovery + ranking
│  ├─ executor.py         # gated actions + pacing
│  ├─ oracle_healer.py    # oracles + heal loop
│  └─ verdict_rca.py      # verdict + RCA + quarantine flag
├─ runtime/
│  ├─ browser_client.py   # Playwright wrapper (async)
│  ├─ browser_manager.py  # shared singleton lifecycle
│  ├─ policies.py         # 5-point gate, pacing
│  └─ discovery.py        # multi-strategy selector discovery
├─ memory/
│  ├─ pom_cache.py        # Redis cache schema + API
│  ├─ intent_memory.py    # semantic intent → selector
│  └─ checkpoints.py      # Postgres checkpointer adapter
├─ telemetry/
│  ├─ tracing.py          # LangSmith trace helpers
│  └─ metrics.py          # counters, timers (optional OTEL)
├─ io/
│  ├─ req_loader.py       # Excel/CSV loader
│  └─ config.py           # env, settings
├─ cli/
│  └─ main.py             # `pacts test --req REQ-123`
├─ alembic/
│  ├─ env.py
│  └─ versions/001_init_checkpoints.py
├─ docker/
│  └─ docker-compose.yml  # postgres, redis
└─ requirements.txt
```

---

## 3) Data Contracts

### 3.1 Requirements (Excel)
Columns (minimal):
- `REQ_ID` (str) • `URL` (str) • `STEPS` (str; newline separated `"Element@Region | action | value?"`) • `EXPECTED` (str/JSON)

### 3.2 RunState (graph/state.py)
```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Dict, Any, Optional

class Failure(str, Enum):
    none = "none"
    not_unique = "not_unique"
    not_visible = "not_visible"
    disabled = "disabled"
    unstable = "unstable"
    out_of_scope = "out_of_scope"
    timeout = "timeout"

class RunState(BaseModel):
    req_id: str
    step_idx: int = 0
    heal_round: int = 0
    context: Dict[str, Any] = Field(default_factory=dict)   # plan, url, etc.
    memory_refs: Dict[str, Any] = Field(default_factory=dict)
    failure: Failure = Failure.none
    thread_id: Optional[str] = None
    last_selector: Optional[str] = None
```

---

## 4) Graph (LangGraph 1.0)

### 4.1 Nodes
- **planner** → parse REQ → intents + initial oracles
- **pom_builder** → Find-First discovery (candidates + ranking) → `plan = [{intent, selector, meta}]`
- **executor** → strict 5-point gate → action
- **oracle_healer** → run assertions; if fail → heal (reveal/reprobe/stability wait)
- **verdict_rca** → verdict, RCA, quarantine flag

### 4.2 Edges
```python
# graph/build_graph.py
g.add_node("planner", planner.run)
g.add_node("pom_builder", pom_builder.run)
g.add_node("executor", executor.run)
g.add_node("oracle_healer", oracle_healer.run)
g.add_node("verdict_rca", verdict_rca.run)

g.set_entry_point("planner")
g.add_edge("planner", "pom_builder")
g.add_edge("pom_builder", "executor")

def route_after_execute(state: RunState) -> str:
    if state.failure == Failure.none and state.step_idx < len(state.context["plan"]):
        return "executor"  # next step
    if state.failure == Failure.none:
        return "verdict_rca"
    if state.heal_round < 3:
        return "oracle_healer"
    return "verdict_rca"

g.add_conditional_edges("executor", route_after_execute,
    {"executor": "executor", "oracle_healer": "oracle_healer", "verdict_rca": "verdict_rca"})

app = g.compile(checkpointer=postgres_checkpointer())
```

> All nodes are **async**. Use `await app.ainvoke(state, config={"configurable": {"thread_id": ...}})`.

---

## 5) Runtime (Playwright)

### 5.1 BrowserClient (runtime/browser_client.py)
```python
from playwright.async_api import async_playwright, Page, ElementHandle

class BrowserClient:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page: Page | None = None

    async def start(self, headless: bool = True):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()

    async def goto(self, url: str):
        await self.page.goto(url, wait_until="domcontentloaded")

    async def query(self, selector: str) -> ElementHandle | None:
        return await self.page.query_selector(selector)

    async def locator_count(self, selector: str) -> int:
        return await self.page.locator(selector).count()

    async def visible(self, el: ElementHandle) -> bool:
        return await el.is_visible()

    async def enabled(self, el: ElementHandle) -> bool:
        return await el.is_enabled()

    async def bbox_stable(self, el: ElementHandle, samples=3, delay_ms=120, tol=2.0) -> bool:
        boxes = []
        for _ in range(samples):
            box = await el.bounding_box()
            if not box:
                return False
            boxes.append(box)
            await self.page.wait_for_timeout(delay_ms)
        keys = ["x", "y", "width", "height"]
        return all(abs(boxes[i][k] - boxes[0][k]) <= tol for i in range(1, len(boxes)) for k in keys)

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
```

### 5.2 BrowserManager (runtime/browser_manager.py)
```python
class BrowserManager:
    _client: BrowserClient | None = None

    @classmethod
    async def get(cls) -> BrowserClient:
        if not cls._client:
            cls._client = BrowserClient()
            await cls._client.start(headless=True)
        return cls._client

    @classmethod
    async def shutdown(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None
```

---

## 6) Policies (runtime/policies.py)

### 6.1 Five-Point Gate
```python
async def five_point_gate(browser: BrowserClient, selector: str, el) -> dict:
    count = await browser.locator_count(selector)  # uniqueness
    return {
        "unique": count == 1,
        "visible": await browser.visible(el),
        "enabled": await browser.enabled(el),
        "stable_bbox": await browser.bbox_stable(el),
        "scoped": True  # frame/shadow validated upstream
    }
```

### 6.2 Anti-bot pacing
- Random 200–800ms between actions
- Exponential backoff on retries
- Jitter on navigations/waits

---

## 7) Discovery (runtime/discovery.py)

**Intent format**: `Element@Region | action | value?`  
Examples:  
- `SearchInput@Header | fill | "playwright"`  
- `SearchButton@Header | click`

**Algorithm (Find-First)**:
1) Try **role+name**: `getByRole("textbox", { name: /search/i })` within region
2) Try **label**: `getByLabel(/search/i)`
3) Try **placeholder**: `getByPlaceholder(/search/i)`
4) Try **relational CSS**: `header :is(input[type=search], input[name*=q i])`
5) Shadow DOM: pierce `>>>`
6) Fallback CSS/XPath (scoped)  
Rank by confidence, run 5-point gate; return first passing candidate.

```python
async def discover_selector(browser, intent) -> dict | None:
    # returns { "selector": str, "score": float, "meta": {...} } or None
    ...
```

---

## 8) Agents (async)

### 8.1 Planner (agents/planner.py)
```python
from ..io.req_loader import load_req
from ..telemetry.tracing import traced

@traced("planner")
async def run(state):
    req = load_req(state.req_id)
    state.context["url"] = req["url"]
    state.context["intents"] = parse_steps(req["steps"])  # list of dicts
    state.context["expected"] = req.get("expected", "")
    return state
```

### 8.2 POM Builder (agents/pom_builder.py)
```python
from ..runtime.browser_manager import BrowserManager
from ..runtime.discovery import discover_selector
from ..telemetry.tracing import traced

@traced("pom_builder")
async def run(state):
    browser = await BrowserManager.get()
    await browser.goto(state.context["url"])

    plan = []
    for step in state.context["intents"]:
        cand = await discover_selector(browser, step)
        if cand:
            plan.append({**step, "selector": cand["selector"], "meta": cand["meta"], "confidence": cand["score"]})
    state.context["plan"] = plan
    return state
```

### 8.3 Executor (agents/executor.py)
```python
from tenacity import retry, stop_after_attempt, wait_exponential
from ..runtime.browser_manager import BrowserManager
from ..runtime.policies import five_point_gate
from ..graph.state import Failure
from ..telemetry.tracing import traced

@traced("executor")
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.6, min=0.2, max=2))
async def run(state):
    browser = await BrowserManager.get()
    step = state.context["plan"][state.step_idx]
    el = await browser.query(step["selector"])
    if not el:
        state.failure = Failure.not_visible
        return state

    gates = await five_point_gate(browser, step["selector"], el)
    if not all(gates.values()):
        state.failure = Failure.unstable
        state.context["gates"] = gates
        state.context["last_selector"] = step["selector"]
        return state

    action = step.get("action", "click").lower()
    if action == "click":
        await el.click()
    elif action == "fill":
        await el.fill(step.get("value", ""))
    else:
        await el.click()

    state.step_idx += 1
    state.failure = Failure.none
    return state
```

### 8.4 Oracle + Healer (agents/oracle_healer.py)
```python
from ..graph.state import Failure
from ..runtime.browser_manager import BrowserManager
from ..telemetry.tracing import traced

async def _reveal(browser, selector):
    await browser.page.locator(selector).scroll_into_view_if_needed()
    await browser.page.wait_for_timeout(250)

@traced("oracle_healer")
async def run(state):
    browser = await BrowserManager.get()
    if state.failure in (Failure.unstable, Failure.not_visible):
        sel = state.context.get("last_selector")
        if sel:
            await _reveal(browser, sel)       # reveal
        state.heal_round += 1
        return state
    return state
```

### 8.5 Verdict & RCA (agents/verdict_rca.py)
```python
from ..telemetry.tracing import traced

@traced("verdict_rca")
async def run(state):
    # compute verdict; attach RCA notes from gates + retries
    return state
```

---

## 9) Memory

### 9.1 Postgres Checkpointer (memory/checkpoints.py)
- Alembic migration `001_init_checkpoints.py` creates `checkpoints` table
- Use LangGraph SQL checkpointer (or custom JSONB)

### 9.2 Redis POM Cache (memory/pom_cache.py)
- Key: `route_hash:intent` → `{selector, confidence, meta, last_success_ts}`
- Confidence decay nightly job

### 9.3 Intent Memory
- `SearchInput@Header` → last-good selector; consulted in discovery

---

## 10) Telemetry (LangSmith)

### 10.1 tracing.py
```python
from contextlib import asynccontextmanager
from langsmith import Client
client = Client()  # uses LANGSMITH_API_KEY

@asynccontextmanager
async def traced(name: str):
    run = client.create_run(name=name, run_type="chain", project_name="PACTS")
    try:
        yield
    finally:
        client.update_run(run_id=run["id"], outputs={"ok": True})
```

- Attributes to log: `selector_used`, `candidate_count`, `gate_results`, `bbox`, `frame_ctx`, `heal_round`, `cost`

---

## 11) IO: Requirements Loader (io/req_loader.py)
```python
import openpyxl

def load_req(req_id: str, path="requirements.xlsx") -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        if str(row[0]).strip() == req_id:
            steps = [s.strip() for s in str(row[2]).splitlines() if s and s.strip()]
            return {"req_id": row[0], "url": row[1], "steps": steps, "expected": row[3]}
    raise ValueError(f"Requirement {req_id} not found")
```

---

## 12) CLI (cli/main.py)
```
pacts test --req REQ-123 [--headless true] [--thread T1]
```

- Loads REQ, builds graph app, sets thread_id (LangGraph), `await app.ainvoke(state)`.

---

## 13) Docker Compose (docker/docker-compose.yml)
- **postgres** (checkpointer) • **redis** (POM cache)
- volumes + healthchecks
- `.env` for DSNs + LANGSMITH_API_KEY

---

## 14) E2E Happy Path
1. `pacts test --req REQ-123`
2. planner → pom_builder (Find-First) → executor (gates) → oracle_healer (if needed) → verdict_rca
3. LangSmith traces; Postgres checkpoints; Redis POM cache

---

## 15) Roadmap

**Week 1 (Claude)**
- Scaffold repo + files per layout
- Implement BrowserManager
- Wire req_loader to planner + parse_steps
- Implement discovery (Find-First)
- Executor with five-point gates

**Week 2**
- Healing strategies (reveal, reprobe, stability wait)
- LangSmith attributes, richer RCA
- Alembic migrations + Postgres checkpointer
- Redis POM cache + confidence decay job

**Week 3**
- Frame/Shadow DOM scoping
- Policy tuning telemetry (nightly)
- Basic dashboard (FastAPI JSON + simple charts)
- Optional MCP bridge

---

## 16) Notes for Claude Code
- All nodes **async**; use shared **BrowserManager**
- Use **strict gates** before any action
- Keep **discovery modular**; return ranked candidates
- Log **all** key attributes to LangSmith
- Start simple; iterate healing strategies after E2E works

---

## 17) Appendix: parse_steps()
```python
def parse_steps(raw_steps: list[str]) -> list[dict]:
    out = []
    for line in raw_steps:
        # "Element@Region | action | value"
        parts = [p.strip() for p in line.split("|")]
        er = parts[0].split("@")
        element = er[0].strip()
        region = er[1].strip() if len(er) > 1 else None
        action = parts[1].strip().lower() if len(parts) > 1 else "click"
        value = parts[2].strip().strip('"') if len(parts) > 2 else None
        out.append({"intent": f"{element}@{region}" if region else element,
                    "element": element, "region": region, "action": action, "value": value})
    return out
```
