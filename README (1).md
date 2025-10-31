# PACTS — Production-Ready Autonomous Testing (Phase 1 ✅)

_Last updated: 2025-10-31 01:09_

**Status:** Phase 1 COMPLETE (commit `efe759f`) — self‑healing autonomous loop validated on real app targets.

## What’s Included
- Six‑agent architecture under **LangGraph 1.0**
- **Planner v2** (authoritative binding; no LLM mutation)
- **POMBuilder** with 3 discovery strategies (≈90% coverage; ROLE_HINTS 16/16)
- **Executor** with five‑point gate; 9 actions
- **OracleHealer v2** (reveal + reprobe + stability) — **85–90% recovery**
- **VerdictRCA** (basic verdicts + metrics; Phase 2 LLM RCA)
- **Generator** (stub; Phase 2 priority)

## Quick Start
```bash
# API
uvicorn backend.api.main:app --reload

# CLI (authoritative input)
python -m backend.cli.main --req REQ-1 --authoritative-json specs/example.json
```

## Phase 2 — Next Up: Generator v2
- Generate Playwright tests from `executed_steps` + `verdict` + `heal_events`
- Jinja2 templates; annotations for healing and selector confidence
- Outputs under `generated_tests/`
- Docs: `docs/GENERATOR-AGENT-V2.md` (to be added)

## Docs
- Blueprint: `docs/PACTS-Phase-1-Final-Blueprint-v3.6.md`
- Healer: `docs/ORACLE-HEALER-V2-DELIVERED.md`
- Session log: `docs/SESSION-2025-10-30-ORACLE-HEALER-V2.md`
