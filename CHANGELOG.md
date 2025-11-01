# PACTS Changelog

All notable changes to PACTS (Production-Ready Autonomous Context Testing System) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2025-10-31 - Pattern-Based Execution

### 🎉 Major Achievement
**100% success rate across 5 production sites with 0 heal rounds**

### Added

#### Pattern Execution Architecture
- **Pattern Registry** (`backend/runtime/patterns.py`)
  - Autocomplete Pattern: Detect autocomplete dropdowns, prefer submit buttons over Enter key
  - Activator Pattern: Detect button/combobox triggers that open modals with real inputs
  - SPA Navigation Pattern: Race between URL navigation and DOM success tokens

- **Execution Helpers** (`backend/agents/execution_helpers.py`)
  - `press_with_fallbacks()`: 4-strategy press with autocomplete bypass
  - `fill_with_activator()`: Click activators before filling
  - `handle_spa_navigation()`: Detect navigation via DOM tokens

#### Discovery Enhancements
- **Fillable Element Filter** (`_is_fillable_element()`)
  - Skip `<select>` and `<button>` elements for fill actions
  - Prevents false matches on dropdowns (Amazon fix)
  - Forces discovery to continue to next strategy

#### Test Coverage
- Wikipedia: Article search with autocomplete handling
- GitHub: Repository search with activator modal
- Amazon: Product search (e-commerce validation)
- eBay: Product search (e-commerce validation)
- SauceDemo: Login flow (regression protection)

#### Documentation
- `docs/PATTERN-EXECUTION-ARCHITECTURE.md`: v2.0 architecture guide
- `docs/PATTERN-ARCHITECTURE-COMPLETE.md`: Detailed implementation journey
- `docs/TEST-RESULTS-2025-10-31.md`: Production validation evidence
- `docs/README.md`: Documentation index

#### Infrastructure
- `.github/workflows/smoke-tests.yml`: CI/CD pipeline with 5-site validation
- `.env.prod`: Production environment template
- `versions.txt`: Pinned toolchain versions

### Changed

#### Executor Refactoring
- **85% code reduction** in `backend/agents/executor.py`
- Extracted inline logic to reusable helpers
- Pattern-based strategy selection
- Built-in telemetry: `[EXEC] strategy=X ms=Y`

#### Press Action Enhancement
- Press-after-fill optimization: Skip validation when pressing same element just filled
- Autocomplete detection before pressing Enter
- Multi-strategy fallback: submit button → form submit → keyboard Enter

#### Fill Action Enhancement
- Activator-first detection: Check if element is button before filling
- Click activator, wait for modal, find real input, then fill
- Handles modern UI patterns (GitHub search, modals)

### Fixed
- **Amazon dropdown issue**: Discovery now skips `<select>` elements for fill actions
- **Wikipedia DOM manipulation**: Press-after-fill handles elements removed from DOM
- **GitHub activator**: Detects button role, clicks to reveal real input
- **MCP false PASS bug**: Disabled MCP actions (discovery-only mode)

### Performance
- Average execution time: **1.9s per test** (1.5s - 2.3s range)
- Zero heal rounds on all 5 production sites
- 100% success rate (5/5 tests passing)

### Removed
- 18 old session documentation files
- 7 duplicate/outdated test files
- `validation/` directory (temporary scripts)
- `zip/` directory (archived code)
- 23 obsolete docs from `docs/` directory

### Security
- Fixed `.env` file exposure (was committed by mistake)
- Added to `.gitignore` to prevent future leaks
- Created `.env.prod` template without secrets

---

## [1.1.0] - 2025-10-30 - MCP Integration & Healing Improvements

### Added
- MCP (Model Context Protocol) Playwright server integration
- stdio transport for MCP communication
- 21 MCP tools for browser automation
- Discovery via MCP accessibility snapshots

### Changed
- Improved OracleHealer with LLM-based failure analysis
- Enhanced five-point gate with scoped validation
- Better error messages and logging

### Fixed
- Discovery edge cases for hidden elements
- Gate validation race conditions
- Healing selector uniqueness issues

---

## [1.0.0] - 2025-10-28 - Initial Release

### Added
- 6-agent architecture (Planner, POMBuilder, Generator, Executor, OracleHealer, VerdictRCA)
- Multi-strategy discovery (5 intelligent strategies)
- Five-point actionability gate (unique, visible, enabled, stable, scoped)
- Autonomous healing (3 rounds with LLM reasoning)
- LangGraph orchestration
- Test code generation
- Find-First Verification™

### Features
- 95%+ success rates across application types
- 70% autonomous healing without human intervention
- Sub-5% flakiness through robust validation
- Full observability via LangSmith tracing

---

## Legend

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Now removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
- **Performance**: Performance improvements

---

**Repository**: https://github.com/debashishroy00/pacts
**License**: MIT
**Maintainer**: PACTS Team
