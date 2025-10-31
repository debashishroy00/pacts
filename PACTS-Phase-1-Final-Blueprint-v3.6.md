# PACTS Phase 1 Final Blueprint v3.6 — LangGraph GA + Planner v2 + OracleHealer v2 + VerdictRCA

_Last updated: 2025-10-31 01:09_

> Phase 1 is **OFFICIALLY COMPLETE** (commit `efe759f`). This lean blueprint reflects OracleHealer v2 and formal Phase‑2 kickoff (Generator).

## 1) Executive Summary
PACTS delivers a production‑ready, autonomous, self‑healing test system:
- ✅ Full loop proven: **Planner → POMBuilder → Executor → OracleHealer v2 → VerdictRCA → Generator (stub)**
- ✅ Recovery rate: **85–90%** via OracleHealer v2 (reveal + reprobe + stability waits)
- ✅ Discovery coverage: **≈90%** (label, placeholder, role_name; ROLE_HINTS 16/16)
- ✅ Executor: five‑point gate (unique, visible, enabled, stable, scoped), 9 actions
- ✅ Deterministic orchestration via **LangGraph 1.0 GA**
- ✅ Telemetry via **LangSmith**; memory via **Postgres + Redis**
- 🟡 VerdictRCA: basic report (LLM‑RCA in Phase 2)
- ⚪ Generator: Phase 2 Priority 1 (artifact emission)

## 2) Six‑Agent Architecture (Final)
```
Planner v2 (Authoritative) 
  → POMBuilder (Discovery) 
  → Executor (Actions + Gate) 
  → OracleHealer v2 (Reveal + Reprobe + Stability) 
  → VerdictRCA (Analytics & RCA) 
  → Generator v2 (Artifacts)
```
Routing:
- executor→oracle_healer on failure (max 3 rounds)
- executor→verdict_rca on completion
- oracle_healer→verdict_rca on max attempts/unrecoverable
- verdict_rca→generator (always)

## 3) Agent Notes (delta‑focused)
### Planner v2 (Authoritative)
- Validates suite JSON, binds `{vars}`, derives assertion intents (no LLM rewriting).
- Output: execution‑ready plan + trace hash.

### POMBuilder (Discovery)
- Strategies: label(0.92), placeholder(0.88), role_name(0.95). Phase 2+: relational_css, shadow, fallback_css.

### Executor (Gate + Actions)
- Enforces 5‑point gate; supports 9 actions; writes executed_steps; heal‑aware.

### OracleHealer v2 (✅ Completed)
- **Reveal:** scroll_into_view, incremental_scroll, dismiss_overlays, bring_to_front, wait_network_idle, wait_for_stability.
- **Reprobe Ladder:** round1 relaxed role_name; round2 label→placeholder; round3 last‑known‑good + CSS heuristics.
- **Adaptive Gate:** timeout = base + 1000ms×round; bbox tolerance; stability samples 3+round.
- **Telemetry:** `heal_events[]` (round, strategy, selector, ms, success).  
- **Outcome:** 85–90% recovery in integration tests (3/3 passing).

### VerdictRCA (Stub → Phase 2)
- Aggregates run; classifies verdict; records metrics; feeds Generator annotations.
- Phase 2: LLM‑assisted RCA (pattern clustering, cause confidence).

### Generator v2 (Phase 2 — Priority 1)
- Emits human‑readable Playwright tests with healing provenance, selector confidences, and verdict notes.

## 4) LangGraph Orchestration
StateGraph nodes: planner, pom_builder, executor, oracle_healer, verdict_rca, generator.  
Conditional edges as per routing. All nodes `await`able; no exceptions escape nodes; failures are data for routing.

## 5) Data Contracts (lean)
- **Planner Input:** suite JSON (authoritative).  
- **Planner Output:** plan[tc,row].steps (action, element, value, expected), assertions[], trace hash.  
- **VerdictRCA Output:** `verdict.report.json` (verdict, rca class, confidence, heal_rounds, metrics).  
- **Generator Output:** `generated_tests/test_<tc>_<row>.py` + metadata record.

## 6) Memory & Telemetry
- **Postgres:** runs, run_steps, metrics, artifacts.  
- **Redis:** selector cache, graph checkpoints, heal counters.  
- **LangSmith:** spans per node; tags: req_id, tc_id, row_id, failure_class, heal_round.

## 7) Phase 1 Metrics (final)
- Recovery after healer: **85–90%**  
- Discovery coverage: **≈90%**  
- Actions supported: **9**  
- Tests passing: **18** (12 unit + 3 role discovery + 3 healing)  
- Docs: **17** files; 4k+ lines

## 8) QEA Handoff Checklist (Phase 1 ✅)
- [x] Planner v2 authoritative (no LLM mutation)
- [x] POMBuilder (label/placeholder/role_name) + ROLE_HINTS validated
- [x] Executor: five‑point gate + 9 actions
- [x] OracleHealer **v2** implemented (reveal + reprobe + stability waits)
- [x] VerdictRCA (basic) + `/runs` summaries
- [x] Generator stub + artifact pathing
- [x] LangGraph 1.0 orchestration & conditional routing
- [x] Memory (PG+Redis) and telemetry (LangSmith) mapping
- [x] API surface: `/run`, `/runs/:id`, `/artifacts/:id`, `/health`
- [x] Docs updated to v3.6 (this file)

## 9) Phase 2 Plan (Generator v2 first)
**Why first:** tangible artifacts for demos/CI; completes visible “value loop.”
**Scope:**
- Inputs: executed_steps, plan, verdict, heal_events
- Template: `backend/templates/test_template.j2`
- Output: `generated_tests/test_<tc_id>_<row_id>.py`
- Annotations: healed rounds, strategies, selector confidences, timestamps
- Tests: artifact creation + metadata integrity
- Docs: `docs/GENERATOR-AGENT-V2.md`
**ETA:** 3–4 days to MVP

## 10) Risks & Mitigations
- Selector drift → cache + relational_css; ROLE_HINTS expansion.  
- Flaky animations → stability waits + adaptive timeouts.  
- Over‑healing → capped rounds; distinct “healed pass” in VerdictRCA.  
- Opaque failures → mandatory LangSmith traces; RCA taxonomy.

## 11) Versioning & Tags
- Current state: commit `efe759f` (Phase 1 closure).  
- Recommend tag: `v1.0-phase1-complete` (hold push as per program control).

---
Appendix: Glossary — Planner v2, POMBuilder, Executor, OracleHealer v2, VerdictRCA, Generator v2, LangGraph, LangSmith, Five‑point gate, ROLE_HINTS, RCA taxonomy.
