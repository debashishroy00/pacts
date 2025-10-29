# PACTS 5-Agent Architecture - Quick Reference

**Version**: 2.0  
**Date**: October 28, 2025  
**Status**: CORRECTED

---

## What Changed

### ❌ OLD (Incorrect - 3 Agents)
```
Planner → Generator → Healer
```

### ✅ NEW (Correct - 5 Agents)
```
Planner → POMBuilder → Generator → Executor → OracleHealer
```

---

## The 5 Agents

### 1️⃣ **Planner Agent**
**Role**: Test Discovery & Flow Control  
**Input**: Excel requirements  
**Output**: `plan.json`  
**Key Tasks**:
- Read Excel requirements registry (external ground truth)
- Query episodic memory for historical patterns
- Generate comprehensive test plan with scenarios, data bindings, policies
- Orchestrate LangGraph state machine

---

### 2️⃣ **POMBuilder Agent**
**Role**: Multi-Strategy Locator Discovery  
**Input**: `plan.json`, target URL, policies  
**Output**: `form.json`  
**Key Tasks**:
- Analyze page structure (Shadow DOM, iframes, dynamic IDs)
- Select optimal discovery strategies (Semantic, Shadow DOM, Iframe, Pattern, Vision)
- Validate through 5-Point Actionability Gate (unique, visible, enabled, stable, interactable)
- Build fallback chains with confidence scores
- **CRITICAL**: Uses VERIFIED selectors from live DOM (not guessing!)

---

### 3️⃣ **Generator Agent**
**Role**: Code Synthesis  
**Input**: `plan.json`, `form.json`  
**Output**: `test.py`, `fixtures.json`, `data_loaders.py`  
**Key Tasks**:
- Generate production-ready Playwright Python tests
- Use verified selectors from POMBuilder (no hallucination!)
- Create async/await patterns
- Generate reusable fixtures
- Apply modern Python standards with type hints

---

### 4️⃣ **Executor Agent**
**Role**: Test Execution & Reporting  
**Input**: `test.py`  
**Output**: `run.report.json`, evidence files  
**Key Tasks**:
- Run Playwright tests in target browser
- Manage complete test execution lifecycle
- Capture comprehensive evidence:
  - Screenshots (key steps & failures)
  - Video recordings (full execution)
  - Playwright traces (detailed debugging)
  - Console logs (JavaScript errors)
  - Network activity (API calls)
  - Performance metrics (page load, latency)
- Generate detailed reports with assertions, failures, timing

---

### 5️⃣ **OracleHealer Agent**
**Role**: Autonomous Test Repair  
**Input**: `run.report.json`, failures  
**Output**: `healing.report.json`, modified test code  
**Key Tasks**:
- Analyze test failures (element not found, timeout, assertion failed, environment)
- Query procedural memory for proven healing strategies with success rates
- Apply healing tactics:
  - Reprobe strategy (try alternative selectors from fallback chains)
  - Wait adjustments (timing-sensitive interactions)
  - Viewport changes (browser config)
  - Data correction (invalid test inputs)
- Validate fixes
- Request human approval via LangGraph interrupt gates when needed
- **Target**: 70% autonomous healing success

---

## Architecture Layers

### Layer 1: Input
- **Excel Requirements Registry** (external ground truth)
- Prevents circular dependency (tests don't assert implementation)

### Layer 2: Orchestration
- **LangGraph 1.0** state machine
- 5-agent pipeline with explicit state transitions
- PostgreSQL checkpointer for durable state
- Human-in-the-loop interrupt gates

### Layer 3: Runtime
- **Universal Web Adapter (UWA)** - policy-driven, site-agnostic
- **5-Point Actionability Gate** - verification before action
- **MCP + Playwright** - browser automation

### Layer 4: Memory
- **Episodic Memory** (PostgreSQL) - Last 100 test runs per requirement
- **Working Memory** (Redis 7+) - Session caching, 1hr TTL
- **Procedural Memory** - Healing strategies with success rates

### Layer 5: Observability
- **LangSmith** - Full trace visibility for every agent execution
- Strategy selection rationale, confidence scores, costs, performance

---

## Key Differentiators

### vs Traditional AI Testing (70-80% success)

**PACTS Achieves 95%+ Success Through**:

1. **Find-First Strategy** (not guess-and-check)
   - Verify selectors against live DOM before generating
   - Traditional: AI hallucinates selectors → fails
   - PACTS: Test selectors first → guaranteed working

2. **5-Point Actionability Gate**
   - Unique: Only one element matches
   - Visible: Actually visible to user
   - Enabled: Not disabled/readonly
   - Stable: Not moving/animating
   - Interactable: Can receive clicks/input

3. **Multi-Strategy Discovery**
   - Semantic (role, label, text)
   - Shadow DOM piercing
   - Iframe traversal
   - Pattern matching
   - Vision-based (optional)

4. **Fallback Chains**
   - Primary selector + alternatives
   - Confidence scores per selector
   - Automatic failover during healing

5. **External Ground Truth** (Excel)
   - Tests validate business requirements
   - NOT code implementation
   - Prevents circular dependency

6. **Three Memory Systems**
   - Episodic: Learn from past runs
   - Working: Session state
   - Procedural: Healing tactics

7. **70% Autonomous Healing**
   - Most failures fixed without human intervention
   - LangGraph interrupt gates for critical decisions

---

## Technology Stack

### Python (LangGraph Orchestration)
```
langgraph==0.1.0     # State machine
langchain==0.1.0     # LLM integration
langsmith==0.1.0     # Observability
playwright==1.56+    # Browser automation
pydantic==2.5.0      # Data validation
```

### TypeScript (CLI, MCP, UWA)
```
@playwright/test@^1.56.0
commander@^11.0.0
chalk@^5.3.0
```

### Databases
```
PostgreSQL 14+   # Episodic memory + checkpoints
Redis 7+         # Working memory
```

### Communication
```
REST API (FastAPI) - Bridge between TypeScript and Python
WebSocket - Real-time state updates
JSON files - Shared artifacts (plan.json, form.json)
```

---

## File Outputs

### By Agent

**Planner**: `plan.json`  
**POMBuilder**: `form.json`  
**Generator**: `test.py`, `fixtures.json`, `data_loaders.py`, `requirements.txt`  
**Executor**: `run.report.json`, `screenshots/*.png`, `videos/*.webm`, `traces/*.zip`  
**OracleHealer**: `healing.report.json`, `modified_test.py`

---

## Success Metrics

### Technical
- **Selector Verification**: 95%+ pass rate (currently 86.5% in prototype)
- **Healing Success**: 70%+ autonomous fixes
- **Test Pass Rate**: 90%+ on first run
- **False Positives**: <5%

### Performance
- **Plan Generation**: <60 seconds
- **POM Building**: <30 seconds per page
- **Code Generation**: <20 seconds
- **Healing**: <60 seconds per failure

### Target Sites
- **SauceDemo**: 75% (proven in prototype)
- **GitHub**: 95% (target)
- **Amazon**: 90% (target)

---

## Development Sequence

### Phase 1: Foundation (Weeks 1-2)
- Python LangGraph environment
- PostgreSQL + Redis setup
- TypeScript REST API bridge

### Phase 2: Agent Implementation (Weeks 3-6)
- **Week 3**: Planner Agent
- **Week 4**: POMBuilder Agent
- **Week 5**: Generator Agent  
- **Week 6**: Executor Agent

### Phase 3: Healing & Integration (Weeks 7-8)
- **Week 7**: OracleHealer Agent
- **Week 8**: Full integration, testing

### Phase 4: Production (Weeks 9-12)
- Optimization
- Observability
- Documentation
- Deployment

---

## Documents for Claude Code

### Core Documents (3)

1. **[PACTS-5-AGENT-ARCHITECTURE.md](computer:///mnt/user-data/outputs/PACTS-5-AGENT-ARCHITECTURE.md)**
   - Complete technical architecture
   - All 5 agent specifications
   - State machine definition
   - Memory systems
   - Technology stack
   - ~6,500 lines

2. **[PACTS-5-AGENT-STARTER.md](computer:///mnt/user-data/outputs/PACTS-5-AGENT-STARTER.md)**
   - Implementation guide
   - Code stubs for all 5 agents
   - TypeScript REST API bridge
   - Testing strategies
   - Verification commands
   - ~2,000 lines

3. **[PACTS-5-AGENT-QUICK-REF.md](computer:///mnt/user-data/outputs/PACTS-5-AGENT-QUICK-REF.md)** (this document)
   - Executive summary
   - Quick reference
   - Key decisions
   - ~500 lines

### Supporting Documents

4. **PRD.md** (already exists)
   - Original product requirements
   - Business context

5. **PACTS-SESSION-CONTEXT.md** (already exists)
   - Project history
   - Current status
   - Completed checkpoints

---

## Critical Decision Required

### TypeScript vs Python for Implementation

**RECOMMENDED: Hybrid Approach**

```
Python Side (LangGraph):
- 5 agent nodes
- State machine orchestration
- Memory management (PostgreSQL, Redis)
- LangSmith observability

TypeScript Side (Runtime):
- CLI interface (already working)
- MCP server (already working)
- Universal Web Adapter (element discovery)
- Playwright browser automation
- Policy engine (already working)

Bridge:
- REST API (FastAPI) for Python → TypeScript calls
- JSON files for shared artifacts
- WebSocket for real-time updates
```

**Why Hybrid?**
- LangGraph is Python-only (state machine required)
- TypeScript UWA already partially built (working CLI)
- Playwright works well in both languages
- REST bridge is straightforward

**Alternative**: Full Python rewrite
- Pros: Single language, simpler
- Cons: Rewrite working TypeScript code, lose momentum

---

## Next Steps

### For Claude Code

1. **Read these documents**:
   - PACTS-5-AGENT-ARCHITECTURE.md (complete specs)
   - PACTS-5-AGENT-STARTER.md (code templates)

2. **Start with Planner Agent** (simplest):
   - Setup Python environment
   - Implement Excel reader
   - Generate plan.json
   - Test with sample data

3. **Build REST bridge**:
   - TypeScript Express server
   - Python FastAPI client
   - Test communication

4. **Implement remaining agents** sequentially:
   - POMBuilder (most complex)
   - Generator
   - Executor
   - OracleHealer

5. **Integrate with LangGraph**:
   - State machine
   - PostgreSQL checkpointer
   - Agent orchestration

---

## Questions to Resolve

1. **Technology Stack**: Confirm hybrid approach (Python + TypeScript)?
2. **REST API**: FastAPI or Flask for Python bridge?
3. **Memory Systems**: Confirm PostgreSQL + Redis?
4. **Observability**: LangSmith or alternative?
5. **Deployment**: Docker, Kubernetes, or serverless?

---

**Version**: 2.0  
**Status**: Ready for Implementation  
**Contact**: DR (Product Owner)  

---
