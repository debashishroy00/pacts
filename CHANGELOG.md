# PACTS Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2-prod-validated] - 2025-11-01

### Added
- **Salesforce Lightning Support**: Full dialog scoping and HITL 2FA integration
  - Dialog-scoped discovery for App Launcher navigation
  - LAUNCHER_SEARCH pattern with auto-navigation detection
  - Smart button disambiguation (filters tabs, close buttons)
  - HITL support for manual 2FA/CAPTCHA intervention
  
- **Centralized Step Utilities** (`backend/runtime/step_utils.py`)
  - `get_step_target()`: Handle LLM field name variations (element/target/intent)
  - `get_step_action()`, `get_step_value()`, `get_step_within()`
  - `normalize_step_fields()`: Convert legacy field names

- **Enhanced URL Navigation Detection** (`backend/agents/executor.py`)
  - Wait for `networkidle` to handle slow networks
  - Check for specific Lightning page types (`/lightning/o/`, `/r/`, `/page/`)
  - More robust than simple URL equality checks

- **Production Deployment Artifacts**
  - `.env.prod`: Production environment template
  - `.github/workflows/smoke-tests.yml`: CI/CD smoke tests
  - `versions.txt`: Pinned toolchain versions
  - `docs/SALESFORCE-FIXES-SUMMARY.md`: Technical documentation

### Fixed
- **Dialog Scoping Bug #1** (`backend/agents/planner.py:74`)
  - Fixed field name mismatch: Planner now checks both `target` and `element` fields
  - Used shared helper `get_step_target()` for consistency

- **Dialog Scoping Bug #2** (`backend/agents/planner.py:358`)
  - Fixed `within` field not propagating from suite to plan
  - Added explicit `"within": st.get("within")` to step dict construction

- **LAUNCHER_SEARCH Timeout** (`backend/agents/executor.py:244-266`)
  - Fixed timeout when Salesforce auto-navigates on Enter keypress
  - Detects URL changes before trying to click result buttons
  - Handles both auto-navigation and manual-click scenarios

- **Button Disambiguation** (`backend/runtime/discovery.py:260-303`)
  - Fixed NOT_UNIQUE errors for common action buttons (New, Save, Edit, Delete)
  - Filters out tab elements using `closest('[role="tab"]')`
  - Filters out close/dismiss buttons using aria-label/title
  - Returns positioned selectors (`nth=0`, `nth=1`) with metadata

### Changed
- **Planner**: Now uses shared `get_step_target()` helper instead of inline field extraction
- **Executor**: Enhanced LAUNCHER_SEARCH with `networkidle` wait and Lightning page type checks
- **Discovery**: Added disambiguation strategy (`role_name_disambiguated`) for ambiguous buttons

### Validated Sites
- Wikipedia (autocomplete pattern) ✅
- GitHub (activator pattern) ✅
- Amazon (e-commerce, fillable filter) ✅
- eBay (e-commerce, autocomplete) ✅
- SauceDemo (regression protection) ✅
- Salesforce Lightning (dialog scoping, HITL 2FA) ✅

### KPIs
- **Success Rate**: 100% (6/6 sites)
- **Heal Rounds**: 0 average
- **Execution Time**: 1.9s average per step
- **Pattern Coverage**: autocomplete, activator, dialog scoping, HITL

---

## [1.1] - 2025-10-30

### Added
- Pattern-based execution architecture
- Pattern registry (autocomplete, activator, SPA navigation)
- Execution helpers with multi-strategy fallbacks
- Enhanced discovery with fillable element filtering

### Fixed
- Refactored executor (85% code reduction)
- 5/5 production sites passing (Wikipedia, GitHub, Amazon, eBay, SauceDemo)

### KPIs
- **Success Rate**: 100% (5/5 sites)
- **Heal Rounds**: 0 average

---

## [1.0] - 2025-10-25

### Added
- Initial PACTS architecture
- Planner, POMBuilder, Executor, OracleHealer agents
- Discovery engine with role_name, label, placeholder strategies
- MCP Playwright integration (discovery-only mode)
- HITL (Human-in-the-Loop) framework

### Validated
- SauceDemo login flow
- Basic e-commerce workflows

---

## Legend
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
