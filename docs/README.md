# PACTS Documentation Index

**Version**: 2.0 (Pattern-Based Execution)
**Last Updated**: 2025-10-31
**Status**: Production Ready

---

## Quick Start

### New to PACTS?
Start here: [PACTS Complete Specification](PACTS-COMPLETE-SPECIFICATION.md)

### Upgrading from v1.x?
Read: [Pattern Execution Architecture](PATTERN-EXECUTION-ARCHITECTURE.md)

### Want to see proof?
Check: [Test Results 2025-10-31](TEST-RESULTS-2025-10-31.md)

---

## Core Documentation

### 1. System Specification
**File**: [PACTS-COMPLETE-SPECIFICATION.md](PACTS-COMPLETE-SPECIFICATION.md)

**What it covers**:
- System vision & philosophy
- 6-agent architecture
- Discovery strategies
- Five-point actionability gate
- Data contracts
- API specifications

**Who should read**: Anyone building PACTS from scratch, architects, new developers

---

### 2. Pattern Execution Architecture (v2.0)

**Primary Doc**: [PATTERN-EXECUTION-ARCHITECTURE.md](PATTERN-EXECUTION-ARCHITECTURE.md)
**Supplementary**: [PATTERN-ARCHITECTURE-COMPLETE.md](PATTERN-ARCHITECTURE-COMPLETE.md)

**What it covers**:
- Evolution from selector-based to pattern-based
- 3 core patterns (Autocomplete, Activator, SPA Nav)
- Execution helpers architecture
- Refactored executor
- Discovery enhancements
- Migration guide

**Who should read**: Developers extending PACTS, pattern contributors, troubleshooters

**Key Sections**:
- Pattern Registry (`backend/runtime/patterns.py`)
- Execution Helpers (`backend/agents/execution_helpers.py`)
- Telemetry & Observability
- Adding new patterns

**Note**: PATTERN-ARCHITECTURE-COMPLETE.md contains the original pattern completion summary with detailed test journey.

---

### 3. Test Results & Validation
**File**: [TEST-RESULTS-2025-10-31.md](TEST-RESULTS-2025-10-31.md)

**What it covers**:
- 5 production site tests (Wikipedia, GitHub, Amazon, eBay, SauceDemo)
- Detailed metrics (heal rounds, execution time, patterns used)
- Screenshot evidence
- Pattern usage analysis
- Performance benchmarks
- Known issues

**Who should read**: QA teams, stakeholders, anyone validating PACTS claims

**Highlights**:
- 100% success rate (5/5 sites)
- 0 heal rounds average
- Full visual verification

---

### 4. MCP Integration
**File**: [PACTS-MCP-ADDENDUM.md](PACTS-MCP-ADDENDUM.md)

**What it covers**:
- Model Context Protocol integration
- Playwright MCP server setup
- Discovery via MCP (21 tools)
- MCP vs local Playwright comparison
- Known limitations

**Who should read**: DevOps, infrastructure engineers, advanced users

**Status**: MCP discovery enabled, actions disabled (separate browser issue)

---

### 5. Phase 1 Blueprint
**File**: [PACTS-Phase-1-Final-Blueprint-v3.6.md](PACTS-Phase-1-Final-Blueprint-v3.6.md)

**What it covers**:
- Original Phase 1 design
- Agent specifications
- Success criteria
- Historical context

**Who should read**: Understanding PACTS evolution, historical reference

**Note**: This is historical. Current spec is in PACTS-COMPLETE-SPECIFICATION.md

---

## Quick Reference

### Architecture Files

| Component | File Location | Purpose |
|-----------|--------------|---------|
| **Patterns Registry** | `backend/runtime/patterns.py` | Define reusable interaction patterns |
| **Execution Helpers** | `backend/agents/execution_helpers.py` | Pattern-specific execution logic |
| **Executor** | `backend/agents/executor.py` | Main action execution agent |
| **Discovery** | `backend/runtime/discovery.py` | Multi-strategy element discovery |
| **Planner** | `backend/agents/planner.py` | NLP requirement parsing |
| **POMBuilder** | `backend/agents/pom_builder.py` | Selector discovery & validation |
| **OracleHealer** | `backend/agents/oracle_healer.py` | Autonomous failure healing |
| **VerdictRCA** | `backend/agents/verdict_rca.py` | Root cause analysis |
| **Generator** | `backend/agents/generator.py` | Test code generation |

---

### Pattern Quick Reference

#### Autocomplete Pattern
**When**: Sites show autocomplete dropdowns that intercept Enter key
**Sites**: Wikipedia, Amazon, eBay
**Strategy**: Detect dropdown → click submit → keyboard Enter fallback

#### Activator Pattern
**When**: "Inputs" are actually buttons that open modals
**Sites**: GitHub, Slack-style search
**Strategy**: Detect button → click → find real input → fill

#### SPA Navigation Pattern
**When**: DOM updates before/instead of URL navigation
**Sites**: React/Vue apps, Wikipedia articles
**Strategy**: Race between `waitForNavigation` and DOM success tokens

---

## Test Suites

### Production Validation Sites

| Site | Test Type | Pattern Used | Status |
|------|-----------|--------------|--------|
| **Wikipedia** | Article search | Autocomplete | ✅ PASS (0 heals) |
| **GitHub** | Repo search | Activator | ✅ PASS (0 heals) |
| **Amazon** | Product search | Autocomplete | ✅ PASS (0 heals) |
| **eBay** | Product search | Autocomplete | ✅ PASS (0 heals) |
| **SauceDemo** | E2E login flow | Direct fill | ✅ PASS (0 heals) |

### Run Tests

```bash
# Wikipedia
python -m backend.cli.main test --req wikipedia_search --headed --slow-mo 800

# GitHub
python -m backend.cli.main test --req github_search --headed --slow-mo 800

# Amazon
python -m backend.cli.main test --req amazon_search --headed --slow-mo 800

# eBay
python -m backend.cli.main test --req ebay_search --headed --slow-mo 800

# SauceDemo
python -m backend.cli.main test --req login_simple --headed --slow-mo 800
```

---

## Version History

### v2.0 (2025-10-31) - Pattern-Based Execution
- ✅ Pattern registry architecture
- ✅ Execution helpers (press, fill, spa_nav)
- ✅ Discovery enhancement (fillable element filtering)
- ✅ 100% success rate across 5 production sites
- ✅ 0 heal rounds average
- ✅ Full telemetry & observability

### v1.x - Find-First Verification
- ✅ 6-agent architecture
- ✅ Multi-strategy discovery
- ✅ Five-point actionability gate
- ✅ Autonomous healing
- ✅ 95%+ success rate
- ✅ 70% autonomous healing

---

## Contributing

### Adding New Patterns

1. **Define pattern** in `backend/runtime/patterns.py`
2. **Create helper** in `backend/agents/execution_helpers.py`
3. **Integrate** in `backend/agents/executor.py`
4. **Test** with production site
5. **Document** in PATTERN-EXECUTION-ARCHITECTURE.md

Example: See Modal Overlay pattern template in docs.

### Documentation Standards

- **Specification docs**: Precise, deterministic, AI-buildable
- **Architecture docs**: Patterns, learnings, design decisions
- **Test results**: Evidence-based, screenshot-verified, metrics-driven

---

## Support & Contact

### Issues
Report bugs or feature requests: GitHub Issues (link TBD)

### Questions
Check docs first, then ask in team channel

### Contributing
See CONTRIBUTING.md (TBD)

---

## License

MIT License - See LICENSE file

---

**Documentation Version**: 2.0
**Last Updated**: 2025-10-31
**Status**: ✅ Current and Complete
