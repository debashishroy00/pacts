# PACTS Documentation Index

**Version**: 2.1 (Enterprise SPA + Type-Ahead Strategy)
**Last Updated**: 2025-11-02
**Status**: Production Ready

---

## Quick Start

### New to PACTS?
Start here: [Main README](../README.md) - Complete system overview with v2.1 achievements

### Want to see Salesforce Lightning in action?
Read: [Salesforce Fixes Summary](SALESFORCE-FIXES-SUMMARY.md) - Technical deep-dive with 100% success story

### Implementing HITL workflows?
Check: [HITL Guide](../hitl/README.md) - Human-in-the-loop with session reuse

---

## Core Documentation

### 1. Salesforce Lightning Deep-Dive (v2.1)
**File**: [SALESFORCE-FIXES-SUMMARY.md](SALESFORCE-FIXES-SUMMARY.md)

**What it covers**:
- Multi-strategy Lightning combobox (type-ahead, aria-controls, keyboard nav)
- App-specific helpers architecture
- SPA page load wait strategy
- Parent clickability detection
- Session reuse implementation
- 100% success story (10/10 steps, 0 heal rounds)

**Who should read**: Developers implementing enterprise SPA support, troubleshooters, anyone extending to SAP/Oracle

**Key Insights**:
- Type-ahead strategy bypasses DOM quirks entirely
- App-specific helpers keep framework agnostic (34% code reduction)
- Page load wait critical for async SPAs

---

### 2. Implementation Journey
**File**: [SESSION-SUMMARY-2025-11-02.md](SESSION-SUMMARY-2025-11-02.md)

**What it covers**:
- Complete implementation timeline
- Session reuse (73.7h/year saved)
- HITL UX improvements
- Debugging process with MCP
- Files modified with line numbers
- Performance impact analysis

**Who should read**: Understanding the evolution from 80% → 100% success, learning debugging techniques

**Highlights**:
- Type-ahead discovery process
- MCP Playwright debugging workflow
- ROI analysis for session reuse

---

### 3. Architecture Overview
**File**: [Main README](../README.md)

**What it covers**:
- System vision & v2.1 achievements
- 6-agent architecture (Planner, POMBuilder, Generator, Executor, OracleHealer, VerdictRCA)
- Pattern registry (autocomplete, activator, SPA navigation)
- Technology stack
- Quick start guide
- 100% success metrics across 6 production sites

**Who should read**: New developers, stakeholders, anyone evaluating PACTS

---

### 4. Release Notes
**File**: [RELEASE-v1.2.md](../RELEASE-v1.2.md)

**What it covers**:
- v2.1 headline achievements
- Multi-strategy Lightning combobox details
- App-specific helpers architecture
- Session reuse implementation
- Validation results with test breakdown
- Key learnings and patterns

**Who should read**: Understanding production readiness, deployment teams

---

### 5. Version History
**File**: [CHANGELOG.md](../CHANGELOG.md)

**What it covers**:
- Semantic versioning of all releases
- Detailed change logs (Added, Fixed, Changed)
- KPIs for each version
- Code references with line numbers

**Who should read**: Tracking changes, understanding version differences

---

## Quick Reference

### Architecture Files (v2.1)

| Component | File Location | Purpose |
|-----------|--------------|---------|
| **Patterns Registry** | `backend/runtime/patterns.py` | Define reusable interaction patterns |
| **Salesforce Helpers** | `backend/runtime/salesforce_helpers.py` | Lightning-specific logic (NEW v2.1) |
| **Execution Helpers** | `backend/agents/execution_helpers.py` | Pattern-specific execution logic |
| **Executor** | `backend/agents/executor.py` | Main action execution agent (34% smaller) |
| **Discovery** | `backend/runtime/discovery.py` | Multi-strategy element discovery + page wait |
| **Planner** | `backend/agents/planner.py` | NLP requirement parsing |
| **POMBuilder** | `backend/agents/pom_builder.py` | Selector discovery & validation |
| **OracleHealer** | `backend/agents/oracle_healer.py` | Autonomous failure healing |
| **VerdictRCA** | `backend/agents/verdict_rca.py` | Root cause analysis |
| **Generator** | `backend/agents/generator.py` | Test code generation |

---

### Pattern Quick Reference (v2.1)

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

#### Type-Ahead Selection (NEW v2.1)
**When**: Custom dropdowns with non-standard option rendering
**Sites**: Salesforce Lightning custom picklists
**Strategy**: Focus combobox → type value → press Enter
**Benefit**: Bypasses DOM quirks, works universally

#### SPA Page Load Wait (NEW v2.1)
**When**: Elements render asynchronously after navigation
**Sites**: Salesforce Lightning, modern SPAs
**Strategy**: `wait_for_load_state("domcontentloaded")` + 1s settle time
**Benefit**: Prevents premature discovery

---

## Test Suites

### Production Validation Sites (v2.1)

| Site | Test Type | Pattern Used | Status |
|------|-----------|--------------|--------|
| **Wikipedia** | Article search | Autocomplete | ✅ PASS (0 heals) |
| **GitHub** | Repo search | Activator | ✅ PASS (0 heals) |
| **Amazon** | Product search | Autocomplete | ✅ PASS (0 heals) |
| **eBay** | Product search | Autocomplete | ✅ PASS (0 heals) |
| **SauceDemo** | E2E login flow | Direct fill | ✅ PASS (0 heals) |
| **Salesforce** | Opportunity creation | Type-Ahead + SPA Wait + HITL | ✅ PASS (10/10, 0 heals) |

### Run Tests

```bash
# All baseline tests
python -m backend.cli.main test --req wikipedia_search --headed
python -m backend.cli.main test --req github_search --headed
python -m backend.cli.main test --req amazon_search --headed
python -m backend.cli.main test --req ebay_search --headed
python -m backend.cli.main test --req login_simple --headed

# Salesforce (first run with HITL 2FA)
python -m backend.cli.main test --req salesforce_opportunity_hitl --headed --slow-mo 800

# Salesforce (subsequent runs, skips 2FA!)
python -m backend.cli.main test --req salesforce_opportunity_postlogin --headed
```

---

## Version History

### v2.1 (2025-11-02) - Enterprise SPA + Type-Ahead
- ✅ **Multi-strategy Lightning combobox** (type-ahead, aria-controls, keyboard nav)
- ✅ **App-specific helpers architecture** (salesforce_helpers.py)
- ✅ **SPA page load wait** (prevents premature discovery)
- ✅ **Session reuse for HITL** (73.7h/year saved)
- ✅ **100% success on Salesforce** (10/10 steps, 0 heal rounds)
- ✅ **Framework-agnostic design** (34% code reduction)

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

### Adding New Enterprise App Support

**Pattern** (proven with Salesforce):
1. **Create app helper module**: `backend/runtime/{app}_helpers.py`
2. **Extract app-specific patterns**: Dialog scoping, custom components
3. **Import in executor**: Keep core logic framework-agnostic
4. **Test with production workflows**: 100% success target
5. **Document patterns**: Share learnings with community

**Example**: Salesforce helpers module (225 lines):
- `handle_launcher_search()`: App-specific modal navigation
- `handle_lightning_combobox()`: Multi-strategy custom dropdown
- Pattern detection utilities: `is_launcher_search()`, `extract_launcher_target()`

**Benefits**:
- Core executor stays clean (34% code reduction)
- Easy to add SAP, Oracle, ServiceNow, etc.
- Patterns are reusable across similar apps

### Adding New Patterns

1. **Define pattern** in `backend/runtime/patterns.py`
2. **Create helper** in `backend/agents/execution_helpers.py`
3. **Integrate** in `backend/agents/executor.py`
4. **Test** with production site
5. **Document** in this README and release notes

### Documentation Standards

- **Clear versioning**: Update version numbers in headers
- **Evidence-based**: Include test results, metrics, code references
- **Actionable**: Provide runnable examples and clear next steps
- **Maintainable**: Remove outdated content, consolidate similar docs

---

## Support & Contact

### Issues
Report bugs or feature requests: [GitHub Issues](https://github.com/debashishroy00/pacts/issues)

### Discussions
Ask questions: [GitHub Discussions](https://github.com/debashishroy00/pacts/discussions)

### Documentation
All docs maintained in [docs/](.) directory with version control

---

## License

MIT License - See LICENSE file

---

**Documentation Version**: 2.1
**Last Updated**: 2025-11-02
**Status**: ✅ Current and Complete
