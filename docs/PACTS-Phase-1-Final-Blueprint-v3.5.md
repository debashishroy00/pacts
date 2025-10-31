# PACTS Phase 1 Final Blueprint v3.5 — LangGraph GA + Planner v2 + VerdictRCA Integration

_Last updated: 2025-10-31 00:02_

---

**📘 Document Relationship**:
- **This document (v3.5)**: Concise quick reference for Phase 1 vision
- **[PACTS-COMPLETE-SPECIFICATION.md](PACTS-COMPLETE-SPECIFICATION.md)**: Complete implementation specification with full code examples
- **Use Case**: Read v3.5 for high-level understanding, use Complete Spec for building from scratch

---

> Purpose: Lean, production-ready blueprint for Phase 1 handoff to QEA.
> Focus: Six-agent architecture, authoritative Planner v2, orchestration with LangGraph 1.0, memory/telemetry, and QEA readiness.
> Style: Concise descriptions + pseudo-snippets (no long code), to be completed with code assistants (Copilot / Claude Code / Cursor).

## 1) Executive Overview


PACTS is an autonomous context testing system built on a six‑agent architecture orchestrated by LangGraph 1.0.  
Phase 1 validates end‑to‑end autonomy on a real web app target (e.g., SauceDemo): plan → discover → execute → heal → analyze → generate.

Key outcomes (Phase 1):
- ✅ Autonomous execution loop proven on a real app (3/3 steps for login scenario)
- ✅ Discovery coverage ≈ 90% via label + placeholder + role_name
- ✅ Executor enforces five‑point actionability gate (unique, visible, enabled, stable, scoped)
- ✅ OracleHealer stubbed (retries up to 3 rounds), v2 roadmap defined
- ✅ VerdictRCA integrated: unified verdict + root-cause attribution
- ✅ Generator produces test artifacts with verdict annotations
- ✅ LangGraph 1.0 GA used for conditional routing + loops
- ✅ Memory (Postgres + Redis) and Telemetry (LangSmith) wired conceptually

## 2) Architecture Summary (Six Agents + Orchestration)


Pipeline (Phase 1, final):

```
Planner v2 (Authoritative) 
  → POMBuilder (Discovery) 
  → Executor (Actions + Gate) 
  → OracleHealer (Retries) 
  → VerdictRCA (Analytics + RCA) 
  → Generator (Artifacts)
```

Control flow (simplified):
- Executor → OracleHealer on failure (with counter; max 3)
- Executor → VerdictRCA on completion (all steps done)
- OracleHealer → VerdictRCA on max attempts or unrecoverable failure
- VerdictRCA → Generator (always)

Trust boundaries:
- Authoritative inputs (user-provided test cases, steps, expected outcomes, test data)
- Deterministic normalization (Planner v2 binds data; no LLM rewriting)
- Observable state transitions (LangSmith traces)

## 3) Agent Breakdown (Lean)


### 3.1 Planner v2 (Authoritative Mode)
Role: Validate provided test cases + steps + outcomes + test data. Bind variables. Normalize assertions. No rediscovery.  
I/O Contract (high level):
- Input: Suite with `testcases[]`, each has steps with `action`, `target`, `value {{var}}` tokens, per‑step `outcome`, plus `data[]` rows.
- Output: Execution‑ready plan with data bound; derived assertion intents added (e.g., `navigates_to:X` → `page_contains_text:X`).

Pseudo‑snippet:
```
validate_schema(payload)
for tc in payload.testcases:
  for row in tc.data or [{}]:
    steps = bind_values(tc.steps, row)       # replaces {{var}} with row values
    asserts = derive_assertions(tc.assertions, steps)  # from outcomes
    plan.append({ tc_id, row_id, steps, asserts })
hash = stable_hash(plan)
emit(plan, trace={req_id, version:"planner_v2", hash})
```

### 3.2 POMBuilder (Discovery)
Role: Map human element labels → stable selectors using multi‑strategy probing.  
Strategies (Phase 1): 
- label (0.92), placeholder (0.88), role_name (0.95).  
Phase 2+: relational_css, shadow_pierce, fallback_css.

Pseudo‑snippet:
```
for step in plan.steps:
  try_label() or try_placeholder() or try_role_name()
  score selector, attach {strategy, score}
```

### 3.3 Executor (Action Engine + Five‑Point Gate)
Role: Execute actions safely on discovered selectors.  
Five‑point gate: unique, visible, enabled, stable_bbox, scoped.  
Actions: click, fill, type, press, select, check, uncheck, hover, focus.  
Writes `executed_steps[]` with traceable metadata.

Pseudo‑snippet:
```
for step in plan.steps:
  sel = step.selector
  if gate.ok(sel):
    do_action(step.action, sel, value?)
    executed_steps.append(...)
  else:
    failure = gate.reason
    route = "oracle_healer"
    break
if all steps done: route = "verdict_rca"
```

### 3.4 OracleHealer (Autonomy Loop, v1 stub)
Role: Improve success odds when gates fail or actions time out.  
v1: increment heal_round; simple re‑probe; retry (max 3).  
v2 roadmap: reveal (scroll, z‑index overlays), reprobe (alternates), stability waits, adaptive timeouts.

Pseudo‑snippet:
```
if state.failure and state.heal_round < 3:
  heal_round += 1
  reprobe_selectors()
  route = "executor"
else:
  route = "verdict_rca"
```

### 3.5 VerdictRCA (Analytics & Root Cause Attribution)  ← NEW Full Agent
Role: Aggregate outcomes, compute unified verdict, classify root causes, and log metrics.  
Taxonomy examples: selector_drift, timing_instability, assertion_mismatch, data_issue, env_fault.  
Artifacts: `verdict.report.json` + DB records; feeds Generator with metadata.

Pseudo‑snippet:
```
collect(executed_steps, failures, heal_rounds, assertions)
verdict = classify(run_outcome)
rca = attribute_root_cause(events, timings, selectors)
write_db(req_id, verdict, rca, metrics)
route = "generator"
```

### 3.6 Generator (Artifact Engine)
Role: Convert validated plan + executed_steps + verdict metadata → runnable Playwright tests.  
Guidelines: Jinja2‑style templates, clear docstrings, include selector strategies as comments, embed verdict notes.

Pseudo‑snippet:
```
template = load("test_template.j2")
code = render(template, plan, executed_steps, verdict, rca)
save("generated_tests/test_<tc_id>_<row_id>.py", code)
```

## 4) LangGraph 1.0 Orchestration (State + Routing)


Core: StateGraph with nodes for each agent; RunState persisted between nodes.

Nodes:
- `planner` → validates & binds (authoritative)
- `pom_builder` → discovers selectors
- `executor` → runs actions + inline assertions
- `oracle_healer` → retries up to 3 rounds
- `verdict_rca` → classifies + logs
- `generator` → emits artifacts

Routing (conceptual):
```
entry = planner
planner -> pom_builder -> executor
executor -(failure)-> oracle_healer
executor -(done)-> verdict_rca
oracle_healer -(max retries or unrecoverable)-> verdict_rca
verdict_rca -> generator -> END
```

Async execution:
- Each node is awaitable (`app.ainvoke(state)`), keeping UI interactions responsive.
- Healing loop uses conditional edges; no exceptions escape nodes.

Observability:
- Each node emits spans to LangSmith; correlation via `req_id` and node labels.

## 5) Data Contracts (Lean JSON)


### 5.1 Planner v2 Input (Authoritative)
```
{
  "req_id": "REQ-LOGIN-001",
  "suite_meta": { "app": "SauceDemo", "area": "Auth", "priority": "P1" },
  "testcases": [
    {
      "tc_id": "TC-Login-Valid",
      "title": "Valid login shows products",
      "steps": [
        { "id": "S1", "action": "fill",  "target": "Username", "value": "{{user}}", "outcome": "field_populated" },
        { "id": "S2", "action": "fill",  "target": "Password", "value": "{{pass}}", "outcome": "field_populated" },
        { "id": "S3", "action": "click", "target": "Login",                 "outcome": "navigates_to:Products" }
      ],
      "assertions": [
        { "id": "A1", "type": "page_contains_text", "target": "Products" }
      ],
      "data": [
        { "row_id": "D1", "user": "standard_user", "pass": "secret_sauce" }
      ]
    }
  ]
}
```

### 5.2 Planner v2 Output (to RunState)
```
{
  "plan": [
    {
      "tc_id": "TC-Login-Valid",
      "row_id": "D1",
      "steps": [
        { "sid": "S1", "action":"fill",  "element":"Username", "value":"standard_user", "expected":"field_populated" },
        { "sid": "S2", "action":"fill",  "element":"Password", "value":"secret_sauce", "expected":"field_populated" },
        { "sid": "S3", "action":"click", "element":"Login",     "expected":"navigates_to:Products" }
      ],
      "assertions": [
        { "aid":"A1", "kind":"page_contains_text", "element":"Products" }
      ]
    }
  ],
  "trace": { "req_id":"REQ-LOGIN-001", "version":"planner_v2", "hash":"<sha256>" }
}
```

### 5.3 VerdictRCA Output (to DB + file)
```
{
  "req_id": "REQ-LOGIN-001",
  "verdict": "pass",
  "steps_passed": 3,
  "steps_failed": 0,
  "heal_rounds": 1,
  "rca": { "class": "timing_instability", "confidence": 0.62, "notes": "1 retry" },
  "metrics": { "t_exec_ms": 5650, "selectors_resolved": 3 }
}
```

## 6) Memory & Telemetry Model


### 6.1 Memory (Postgres + Redis)
- **Postgres**: persistent records (runs, verdicts, RCA, metrics, artifacts index)
- **Redis**: ephemeral state (graph checkpoints, selector cache, healing counters)

Tables (indicative):
- `runs(req_id, suite_meta, started_at, finished_at, verdict, rca_class, heal_rounds)`
- `run_steps(run_id, step_idx, action, selector, outcome, status, t_ms)`
- `metrics(run_id, key, value)`
- `artifacts(run_id, path, type, hash)`

### 6.2 Telemetry (LangSmith)
- Node spans labeled `planner|pom_builder|executor|healer|verdict|generator`
- Tags: `req_id`, `tc_id`, `row_id`, `failure_class`, `heal_round`
- Use traces for replay, step‑wise timing, RCA evidence

## 7) FastAPI Interface (Lean)


- `POST /run` → kicks off a run with authoritative JSON (Planner v2 input). Returns `req_id`.
- `GET /runs/{req_id}` → run summary (verdict, RCA, metrics).
- `GET /runs/{req_id}/steps` → executed steps with outcomes.
- `GET /artifacts/{req_id}` → generated test files list + hashes.
- `GET /health` → service health.

Security: API key header or bearer token (env‑configurable). CORS allowed for internal dashboard.

## 8) Phase 1 Metrics (Reality Snapshot)


- Discovery coverage: ~90% (label + placeholder + role_name)
- Actions supported: 9
- Healing: up to 3 retries (v1 stub; v2 adds reveal/reprobe/stability waits)
- Tests: representative unit/integration suite (expand in Phase 2)
- Real‑world validation: SauceDemo login (3/3 steps)
- Artifacts: generated tests with verdict annotations

## 9) QEA Handoff Checklist (Ready)


- [ ] **Planner v2 Authoritative Mode**: Validates + binds inputs; no LLM reinterpretation
- [ ] **POMBuilder**: label / placeholder / role_name strategies wired
- [ ] **Executor**: five‑point gate enforced; 9 actions supported
- [ ] **OracleHealer (v1)**: healing loop (max 3); v2 roadmap documented
- [ ] **VerdictRCA**: verdict + RCA classification persisted; API exposed
- [ ] **Generator**: emits test artifacts with verdict annotations
- [ ] **LangGraph**: conditional edges configured exactly as pipeline
- [ ] **Memory/Telemetry**: Postgres/Redis + LangSmith mapping clear
- [ ] **FastAPI**: `/run`, `/runs/:id`, `/artifacts/:id`, `/health` documented
- [ ] **Docs**: this blueprint in `/docs`; deck updated to 6‑agent visuals

## 10) Implementation Cues for Code Assist


- Prefer small, composable functions per agent (`run(state) -> state`).
- Strict dataclasses/Pydantic for RunState; keep fields flat and explicit.
- Never raise from agent nodes; return failure enums for routing.
- Log durations per step and per node; attach to LangSmith spans.
- Use deterministic hashing for plan/signature idempotency.
- Template generator with simple Jinja‑style tokens; avoid metaprogramming.
- Guardrails: cap healing rounds; enforce timeouts; sanitize selectors.

## 11) Risks & Mitigations


- **Selector brittleness** → Mitigate via role_name + relational_css; store last‑known selector as cache hint.
- **Flaky timing** → Stability waits; adaptive timeouts; retry backoff in healer v2.
- **Over‑healing** → Cap retries; classify “healed” vs “pass” distinctly in VerdictRCA.
- **Opaque failures** → Mandatory LangSmith traces; RCA taxonomy enforced.
- **Artifact drift** → Regenerate on schema changes; embed version tags in headers.

## 12) Roadmap (Phase 2/3)


**Phase 2**
- OracleHealer v2: reveal/reprobe/stability waits; adaptive strategies
- Generator v2: richer templates, page objects, fixtures
- Integration test suite expansion (ROLE_HINTS matrix)

**Phase 3**
- MCP bridge, semantic memory, dashboard UX, drift detection
- Multi‑app adapters; enterprise integrations (Jira/TestRail)

## Appendix A) Glossary


- Planner v2: Authoritative validator/binder
- POMBuilder: Selector discovery engine
- Executor: Action engine with gates
- OracleHealer: Self-healing loop
- VerdictRCA: Analytics + RCA
- Generator: Artifact emitter
- LangGraph: Graph orchestration runtime
- LangSmith: Trace/telemetry platform
- Five-point gate: unique/visible/enabled/stable/scoped
- ROLE_HINTS: mapping action keywords → ARIA roles
- RCA taxonomy: drift/timing/logic/data/env
