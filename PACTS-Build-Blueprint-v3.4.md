
# PACTS-Build-Blueprint-v3.4

Status: FINAL (QEA-Ready) • Language: **Python only** • Target: Phase 1 MVP → Production Handoff

---

## 0) Purpose and Evolution

PACTS (Playwright Agents Autonomous Context Testing System) v3.4 consolidates the PowerPoint vision, v3.3 implementation blueprint, and architectural reconciliation from October 2025 into one authoritative, QEA‑ready document.

v3.4 defines a **complete 6-agent architecture** delivering both runtime execution and test artifact generation in Phase 1 MVP.

Core design: LangGraph 1.0 GA orchestration + async Playwright + Postgres/Redis memory + LangSmith observability.

---

## 1) Stack & Versions (Pinned)

| Component | Version | Purpose |
|------------|----------|----------|
| python | 3.11+ | Core runtime |
| langgraph | >=1.0.0,<2.0.0 | Deterministic orchestration |
| playwright | >=1.45,<2.0 | Browser automation |
| fastapi | latest | Dashboard & APIs |
| pydantic | >=2.6,<3.0 | Models & validation |
| psycopg[binary] | >=3.2,<4.0 | Postgres driver |
| redis | >=5.0,<6.0 | Cache & working memory |
| langsmith | >=0.1.39 | Observability & telemetry |
| tenacity | >=8.2 | Retry policies |
| alembic | >=1.13 | Migrations |
| structlog | latest | Structured logging |
| python-dotenv | latest | Env config |

> MVP decision: Direct Playwright first; MCP bridge in Phase 3.

---

## 2) Agents Overview

### Phase 1 – Complete MVP (6 Agents)
1. **Planner** → parse Excel → intents, expected outcomes
2. **POMBuilder** → Find-First discovery → verified selectors
3. **Generator** → create `test.py` + fixtures from verified selectors
4. **Executor** → perform actions (Playwright async)
5. **OracleHealer** → heal failed selectors/actions
6. **VerdictRCA** → verdict, RCA, metrics, quarantine flag

**Pipeline Flow:**
```
Planner → POMBuilder → Generator → Executor → OracleHealer → VerdictRCA
```

### Phase 2 – Enhanced Features
- Advanced healing strategies, confidence scoring improvements

### Phase 3 – Enterprise Additions
- MCP integration, semantic memory, multi-tenant telemetry

---

## 3) Repository Layout

```text
pacts/
├─ backend/                      # Python backend (Phase 1)
│  ├─ graph/
│  │  ├─ state.py
│  │  ├─ build_graph.py
│  │  └─ nodes/
│  ├─ agents/
│  │  ├─ planner.py
│  │  ├─ pom_builder.py
│  │  ├─ generator.py
│  │  ├─ executor.py
│  │  ├─ oracle_healer.py
│  │  └─ verdict_rca.py
│  ├─ runtime/
│  │  ├─ browser_client.py
│  │  ├─ browser_manager.py
│  │  ├─ policies.py
│  │  └─ discovery.py
│  ├─ memory/
│  │  ├─ postgres_cp.py
│  │  ├─ redis_cache.py
│  │  └─ intent_memory.py
│  ├─ telemetry/
│  │  ├─ tracing.py
│  │  └─ metrics.py
│  ├─ api/                       # FastAPI REST endpoints
│  │  ├─ main.py
│  │  ├─ routes/
│  │  │  ├─ verdicts.py
│  │  │  ├─ runs.py
│  │  │  ├─ requirements.py
│  │  │  └─ health.py
│  │  └─ models/
│  │     ├─ request_models.py
│  │     └─ response_models.py
│  ├─ cli/
│  │  └─ main.py
│  ├─ tests/
│  │  ├─ unit/
│  │  ├─ integration/
│  │  └─ e2e/
│  ├─ alembic/                   # DB migrations
│  │  └─ versions/
│  ├─ requirements.txt
│  ├─ pyproject.toml
│  └─ .env.example
│
├─ frontend/                     # Angular 18 UI (Phase 3)
│  ├─ src/
│  │  ├─ app/
│  │  │  ├─ features/
│  │  │  │  ├─ dashboard/       # Main dashboard
│  │  │  │  ├─ requirements/    # Requirements management
│  │  │  │  ├─ test-runs/       # Test execution & results
│  │  │  │  ├─ verdicts/        # Verdict viewing
│  │  │  │  └─ settings/        # Configuration
│  │  │  ├─ core/
│  │  │  │  ├─ services/        # API services
│  │  │  │  ├─ guards/          # Auth guards
│  │  │  │  └─ interceptors/    # HTTP interceptors
│  │  │  └─ shared/
│  │  │     ├─ components/      # Reusable components
│  │  │     └─ models/          # TypeScript interfaces
│  │  ├─ assets/
│  │  └─ environments/
│  ├─ angular.json
│  ├─ package.json
│  └─ tsconfig.json
│
├─ docker/
│  ├─ docker-compose.yml         # Postgres + Redis + Backend + Frontend
│  ├─ backend.Dockerfile
│  └─ frontend.Dockerfile
│
├─ generated_tests/              # Output from Generator agent
│  └─ REQ-XXX/
│     ├─ test.py
│     ├─ fixtures.json
│     └─ data_loaders.py
│
├─ docs/
│  ├─ archive/
│  └─ api/                       # API documentation
│
└─ README.md
```

---

## 4) Data Contracts

### 4.1 Requirement Sheet (Excel)
| Column | Type | Description |
|---------|------|-------------|
| REQ_ID | str | Unique ID |
| URL | str | Target URL |
| STEPS | str | newline-separated “Element@Region | action | value?” |
| EXPECTED | str/JSON | Optional expected results |

### 4.2 RunState
```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Dict, Any, Optional

class Failure(str, Enum):
    none = "none"
    not_unique = "not_unique"
    not_visible = "not_visible"
    disabled = "disabled"
    unstable = "unstable"
    timeout = "timeout"

class RunState(BaseModel):
    req_id: str
    step_idx: int = 0
    heal_round: int = 0
    context: Dict[str, Any] = Field(default_factory=dict)
    failure: Failure = Failure.none
    last_selector: Optional[str] = None
    verdict: Optional[str] = None
```

---

## 5) LangGraph (1.0 GA)

```python
# Add all 6 agent nodes
g.add_node("planner", planner.run)
g.add_node("pom_builder", pom_builder.run)
g.add_node("generator", generator.run)
g.add_node("executor", executor.run)
g.add_node("oracle_healer", oracle_healer.run)
g.add_node("verdict_rca", verdict_rca.run)

# Linear flow through pipeline
g.set_entry_point("planner")
g.add_edge("planner", "pom_builder")
g.add_edge("pom_builder", "generator")
g.add_edge("generator", "executor")

# Conditional routing after execution
g.add_conditional_edges(
    "executor",
    route_after_execute,
    {"executor": "executor", "oracle_healer": "oracle_healer", "verdict_rca": "verdict_rca"}
)

# Conditional routing after healing
g.add_conditional_edges(
    "oracle_healer",
    route_after_heal,
    {"executor": "executor", "verdict_rca": "verdict_rca"}
)
```

All nodes async; invoke via `await app.ainvoke(state)`.

---

## 6) Runtime Components

### 6.1 BrowserClient
Async Playwright wrapper (start, goto, query, visible, enabled, bbox_stable).

### 6.2 BrowserManager
Singleton controlling BrowserClient lifecycle.

### 6.3 Policies
5‑point gate (`unique`, `visible`, `enabled`, `stable_bbox`, `scoped`), random pacing, exponential backoff.

### 6.4 Discovery
Multi‑strategy selector discovery (role+name, label, placeholder, relational CSS, shadow DOM). Returns ranked candidates.

---

## 7) Agents (Async)

### 7.1 Planner
Loads Excel, extracts intents.

### 7.2 POMBuilder
Navigates to URL, discovers selectors, stores plan.
- Uses multi-strategy discovery
- Validates through 5-point gate
- Builds fallback chains with confidence scores
- Output: context["plan"] with verified selectors

### 7.3 Generator
Transforms verified selectors from POMBuilder into Playwright test.py file.
- Input: context["plan"] with verified selectors
- Output: test.py, fixtures.json, data_loaders.py saved to disk
- Uses Jinja2 templates for code generation
- Generates async/await Playwright patterns
- Includes retry logic and proper error handling

### 7.4 Executor
Executes steps; enforces 5‑point gate; records failure state.
- Can execute either: generated test.py OR intents directly
- Captures screenshots, traces, logs
- Sets failure state for healing

### 7.5 OracleHealer
If failure: reveal, reprobe, or stability‑wait; increments heal_round.
- Tries up to 3 heal rounds
- Routes back to Executor for retry or to VerdictRCA if max attempts reached

### 7.6 VerdictRCA
Aggregates results → pass_rate, metrics, RCA notes → Postgres.
- Computes final verdict (pass/fail)
- Generates RCA report
- Sets quarantine flag for flaky tests
- Stores to database for historical analysis

---

## 8) Memory Systems

| Concept | Implementation | Purpose |
|----------|----------------|----------|
| Episodic | Postgres Checkpointer | Run history persistence |
| Procedural | Redis POM Cache | Selector confidence |
| Semantic | Intent Memory | Intent→selector mapping |
| Working | Redis Session Cache | Live run state |

---

## 9) Telemetry (LangSmith)

`tracing.py` implements async context manager for node spans; records selector_used, gate_results, heal_round, and RCA summary.

---

## 10) FastAPI Dashboard

Routes:
- `/health` → service status  
- `/verdicts/{run_id}` → step verdicts  
- `/verdicts/{run_id}/metrics` → pass/fail counts  
- `/runs` → recent runs  
- `/traces/{trace_id}` → LangSmith deep‑link

---

## 11) CLI Usage

```
pacts test --req REQ-001 [--headless true]
```

Loads requirement, builds graph, invokes async flow.

---

## 12) Docker Compose

Includes api, postgres, redis.  
Ports: 8000 (API), 5432 (Postgres), 6379 (Redis).

---

## 13) E2E Happy Path

1. `pacts test --req REQ-001`
2. **planner** → **pom_builder** → **generator** → **executor** → **oracle_healer** (if needed) → **verdict_rca**
3. Outputs: test.py file saved, verdict saved, metrics computed, traces in LangSmith

---

## 14) Roadmap

| Phase | Duration | Features |
|-------|-----------|-----------|
| 1 | Weeks 1–2 | **Backend MVP**: 6 agents, FastAPI REST APIs, CLI. Generates test.py files. Full telemetry, Postgres/Redis |
| 2 | +2 weeks | **Enhanced Features**: Advanced healing strategies, confidence scoring, discovery patterns |
| 3 | +4 weeks | **Angular 18 Frontend**: Dashboard UI, requirements management, test execution interface, real-time updates via WebSockets |
| 4 | +4 weeks | **Enterprise**: MCP bridge, semantic memory, multi-tenant support, advanced analytics |

---

## 14.1) Angular 18 Frontend (Phase 3)

### Features Overview

**Dashboard:**
- Real-time test execution status
- Pass/fail rate charts
- Recent test runs timeline
- System health indicators

**Requirements Management:**
- Upload/edit Excel requirements
- Visual requirement editor
- Requirement versioning
- Bulk operations

**Test Execution:**
- Trigger tests via UI
- Live execution progress
- Step-by-step visualization
- Screenshot/video viewing

**Verdicts & Analytics:**
- Detailed verdict viewing
- RCA reports with drill-down
- Historical trends
- Flakiness detection dashboard

**Settings:**
- Policy configuration
- Browser settings
- Notification preferences
- User management (Phase 4)

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Angular 18 (standalone) | Modern reactive UI |
| State Management | NgRx Signals | Reactive state |
| UI Components | Angular Material | Component library |
| Charts | ngx-charts | Data visualization |
| Real-time | WebSocket (Socket.io) | Live updates |
| API Client | HttpClient + Interceptors | REST communication |

### API Integration

**Backend Endpoints (FastAPI):**
```typescript
// Requirements
GET    /api/requirements
POST   /api/requirements/upload
GET    /api/requirements/{req_id}
PUT    /api/requirements/{req_id}
DELETE /api/requirements/{req_id}

// Test Execution
POST   /api/runs/trigger          // Trigger test run
GET    /api/runs                  // List runs
GET    /api/runs/{run_id}         // Run details
GET    /api/runs/{run_id}/status  // Live status
WS     /ws/runs/{run_id}          // WebSocket updates

// Verdicts
GET    /api/verdicts/{req_id}
GET    /api/verdicts/{req_id}/metrics
GET    /api/verdicts/{req_id}/rca

// Dashboard
GET    /api/dashboard/stats
GET    /api/dashboard/trends

// Health
GET    /api/health
```

### Angular Project Structure

```
frontend/src/app/
├─ features/
│  ├─ dashboard/
│  │  ├─ dashboard.component.ts
│  │  ├─ dashboard.component.html
│  │  └─ components/
│  │     ├─ stats-card/
│  │     ├─ recent-runs/
│  │     └─ health-indicator/
│  ├─ requirements/
│  │  ├─ list/
│  │  ├─ editor/
│  │  └─ upload/
│  ├─ test-runs/
│  │  ├─ list/
│  │  ├─ detail/
│  │  └─ execution-view/
│  └─ verdicts/
│     ├─ list/
│     └─ detail/
├─ core/
│  ├─ services/
│  │  ├─ api.service.ts
│  │  ├─ websocket.service.ts
│  │  └─ auth.service.ts
│  └─ interceptors/
│     └─ auth.interceptor.ts
└─ shared/
   ├─ components/
   │  ├─ page-header/
   │  ├─ loading-spinner/
   │  └─ error-display/
   └─ models/
      ├─ requirement.model.ts
      ├─ test-run.model.ts
      └─ verdict.model.ts
```

---

## 15) QEA Handoff Checklist

- ✅ 6 agents implemented (Planner, POMBuilder, Generator, Executor, OracleHealer, VerdictRCA)
- ✅ LangGraph 1.0 GA wired with all nodes
- ✅ Async Playwright executor validated
- ✅ Generator creates test.py files with fixtures
- ✅ Postgres/Redis functional
- ✅ Verdict API accessible
- ✅ LangSmith telemetry visible for all agents

---

## 16) Success Metrics

| Metric | Target |
|--------|--------|
| Selector discovery accuracy | ≥95% |
| Healing success | ≥70% |
| LangSmith trace coverage | 100% |
| Pass rate reporting | live via API |
| Test.py generation success | ≥95% (Phase 1) |
| Generated tests execute successfully | ≥90% (Phase 1) |

---

## 17) Appendix

### parse_steps()
```python
def parse_steps(raw_steps: list[str]) -> list[dict]:
    out = []
    for line in raw_steps:
        parts = [p.strip() for p in line.split("|")]
        er = parts[0].split("@")
        element = er[0].strip()
        region = er[1].strip() if len(er) > 1 else None
        action = parts[1].strip().lower() if len(parts) > 1 else "click"
        value = parts[2].strip().strip('"') if len(parts) > 2 else None
        out.append({"intent": f"{element}@{region}" if region else element,
                    "element": element, "region": region,
                    "action": action, "value": value})
    return out
```

---

*This document supersedes v3.3 and serves as the authoritative build reference for QEA and Claude Code implementations.*
