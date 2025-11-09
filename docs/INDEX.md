# PACTS v3.0 - Documentation Index

**Last Updated**: 2025-11-08 (v3.1s Phase 4a COMPLETE - 80% Pass Rate Achieved)
**Purpose**: Master index for all PACTS documentation
**Latest Release**: v3.1s Phase 4a (Stealth 2.0 + Hidden Element Activation + Non-Unique Selector Handling + Booking/YouTube/Reddit Fixes)

---

## 📖 Quick Navigation

| Category | Description | Key Files |
|----------|-------------|-----------|
| **[Getting Started](#-getting-started)** | Setup, installation, quick start | QUICK-START.md, DOCKER-SETUP.md |
| **[Technical Specs](#-technical-specifications)** | Architecture, design, blueprints | PACTS-TECHNICAL-SPEC-v2.1.md |
| **[Validation Reports](#-validation--testing-reports)** | Test results, metrics, findings | DAY-15-LIGHTNING-VALIDATION.md |
| **[Implementation Plans](#-implementation-plans)** | Roadmaps, action plans | PACTS-v3.0-IMPLEMENTATION-PLAN.md |
| **[Troubleshooting](#-troubleshooting--fixes)** | Known issues, solutions | WINDOWS-DOCKER-NETWORKING-ISSUE.md |
| **[Session Notes](#-session-notes--summaries)** | Daily logs, progress tracking | SESSION-SUMMARY-2025-11-03.md |
| **[Archive](#-archive--deprecated)** | Outdated/historical docs | RELEASE-v1.2.md, Phase-1 docs |

---

## 🚀 Getting Started

### Essential Setup Guides

| File | Purpose | Status | Last Updated |
|------|---------|--------|--------------|
| **[QUICK-START.md](QUICK-START.md)** | Fast setup guide (5 minutes) | ✅ Current | 2025-11-08 |
| **[TESTING-INSTRUCTIONS.md](../TESTING-INSTRUCTIONS.md)** | 🆕 Complete testing guide | ✅ Current | 2025-11-08 |
| **[DOCKER-SETUP.md](DOCKER-SETUP.md)** | Docker environment setup | ✅ Current | 2025-11-02 |
| **[README.md](README.md)** | Project overview | ✅ Current | 2025-11-02 |

**Start Here**: If you're new to PACTS, read [QUICK-START.md](QUICK-START.md) first.
**Ready to Test**: See [TESTING-INSTRUCTIONS.md](../TESTING-INSTRUCTIONS.md) for running the 23-test suite with v3.1s.

---

## 📐 Technical Specifications

### Architecture & Design

| File | Purpose | Status | Version |
|------|---------|--------|---------|
| **[PACTS-v3.1s-IMPLEMENTATION.md](PACTS-v3.1s-IMPLEMENTATION.md)** | 🆕 v3.1s Universal Mode implementation | ✅ **LATEST** | v3.1s |
| **[PACTS-TECHNICAL-SPEC-v2.1.md](PACTS-TECHNICAL-SPEC-v2.1.md)** | Complete technical specification | ✅ Current | v2.1 |
| **[PACTS-COMPLETE-SPECIFICATION.md](PACTS-COMPLETE-SPECIFICATION.md)** | Comprehensive feature spec | ✅ Current | v3.0 |
| **[PACTS-Phase-1-Final-Blueprint-v3.5.md](PACTS-Phase-1-Final-Blueprint-v3.5.md)** | Phase 1 architecture blueprint | ⚠️ Historical | v3.5 (Phase 1) |

**Latest**: [PACTS-v3.1s-IMPLEMENTATION.md](PACTS-v3.1s-IMPLEMENTATION.md) - Universal testing for any website (stealth mode, friendly CLI, data-driven)
**Technical Reference**: [PACTS-TECHNICAL-SPEC-v2.1.md](PACTS-TECHNICAL-SPEC-v2.1.md) - Authoritative architecture documentation

---

## ✅ Validation & Testing Reports

### v3.1s Phase 4 - QA Validation (Current)

| File | Purpose | Status | Test Count |
|------|---------|--------|------------|
| **[PACTS-v3.1s-VALIDATION-PLAN.md](PACTS-v3.1s-VALIDATION-PLAN.md)** | 🆕 Phase 4a-4c validation plan | ✅ **Phase 4a COMPLETE** | 3 phases |
| **[PHASE-4A-COMPLETION-REPORT.md](PHASE-4A-COMPLETION-REPORT.md)** | 🆕 Phase 4a final report | ✅ **80% PASS RATE** | Complete results |
| **[PHASE-4A-IMPLEMENTATION-SUMMARY.md](PHASE-4A-IMPLEMENTATION-SUMMARY.md)** | Phase 4a implementation report | ✅ Historical | Initial implementation |
| **[TEST-EXECUTION-SUMMARY.md](TEST-EXECUTION-SUMMARY.md)** | Initial test run results | ✅ Historical | Baseline (40% pass) |
| **[PACTS-v3.1s-VALIDATION.md](PACTS-v3.1s-VALIDATION.md)** | Phase 4b validation matrix | 📋 **READY TO RUN** | 5 suites |
| **[REQUIREMENTS-TEST-MATRIX.md](REQUIREMENTS-TEST-MATRIX.md)** | Complete test suite review | 📋 Reference | 23 tests |
| **[TESTING-INSTRUCTIONS.md](../TESTING-INSTRUCTIONS.md)** | Testing guide and commands | ✅ Current | All tests |

**Phase 4a Status** (2025-11-08) - ✅ **COMPLETE**:
- ✅ Stealth 2.0: playwright-stealth integration, human-like behavior, CAPTCHA detection (Stack Overflow/Booking.com detected)
- ✅ Hidden Element Activation: Auto-activate collapsed search bars (GitHub passing with 0 heals)
- ✅ Non-Unique Selector Handling: Text fallback + nth strategies (YouTube video detection working)
- ✅ **Result**: 40% → **80% pass rate** (4/5 core tests passing)
- ✅ Site-Specific Strategies: YouTube videos, Booking.com destination, Reddit search
- ✅ Bug Fixes: Readiness gate None check, healer identical retry loop, role locator syntax

**Validation Suite** ([tests/validation/](../tests/validation/)):
- `static_sites.yaml` - GitHub, Python Docs, Wikipedia
- `spa_sites.yaml` - React, Vue, Angular (SPA testing)
- `auth_flows.yaml` - Login forms and authentication
- `multi_dataset.yaml` + `users.csv` - Data-driven execution
- `run_validation.sh/.bat` - Automated validation runner

**How to Run**:
```bash
cd tests/validation
./run_validation.sh  # Linux/Mac
run_validation.bat   # Windows
```

**Latest Results**:
- **v3.1s Implementation**: [PACTS-v3.1s-IMPLEMENTATION.md](PACTS-v3.1s-IMPLEMENTATION.md) - **PHASES 1-3 COMPLETE** (Ready for validation)
- **Week 8 Phase A+B**: [WEEK-8-PHASE-A-HANDOFF.md](WEEK-8-PHASE-A-HANDOFF.md) - **PRODUCTION READY** (38/38 steps, 0 heals, 13 scope resolutions)

### Week 9 Phase C - Executor Intelligence (Deferred)

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| **[EXECUTOR-INTELLIGENCE-CORE.md](EXECUTOR-INTELLIGENCE-CORE.md)** | Week 9 MVP - Top 3 tools | ⏸️ **DEFERRED** | Dialog Sentinel dropped (too complex for edge cases) |
| **[PHASE-C-INTELLIGENT-AGENT.md](PHASE-C-INTELLIGENT-AGENT.md)** | Phase C architecture spec | 📋 Planning | LSN + Runtime Adaptation (future work) |
| **[api/WEEK-9-SENTINEL-VALIDATION.md](api/WEEK-9-SENTINEL-VALIDATION.md)** | Week 9 Sentinel validation | ⚠️ Reference | False positive issues documented |
| **[DIALOG-SENTINEL-POC.md](DIALOG-SENTINEL-POC.md)** | Dialog Sentinel implementation | 📦 Archived | POC complete but not production-ready |

### Salesforce Lightning Testing (Week 8 - Baseline)

| File | Purpose | Status | Key Findings |
|------|---------|--------|--------------|
| **[WEEK-8-PHASE-A-HANDOFF.md](WEEK-8-PHASE-A-HANDOFF.md)** | Week 8 Phase A+B - EDR validation | ✅ Production Ready | ✅ 100% PASS - 38/38 steps, 0 heals |
| **[WEEK-4-7-VALIDATION-REPORT.md](WEEK-4-7-VALIDATION-REPORT.md)** | Week 4-7 comprehensive validation | ✅ Reference | Weeks 4-6 PRODUCTION READY |
| **[DAY-15-LIGHTNING-VALIDATION.md](DAY-15-LIGHTNING-VALIDATION.md)** | Week 3 validation | ✅ Reference | 100% PASS (Phase 2a bypass) |
| **[SALESFORCE-VALIDATION-REPORT.md](SALESFORCE-VALIDATION-REPORT.md)** | Week 3 standalone summary | ✅ Reference | Session-scoped cache + bypass |
| **[DAY-9-FINAL-RESULTS.md](DAY-9-FINAL-RESULTS.md)** | Day 9 Lightning blocker findings | ✅ Reference | "New" button timeout identified |

### Historical Test Reports (Week 2)

| File | Purpose | Status | Key Findings |
|------|---------|--------|--------------|
| **[DAY-13-14-REPORT.md](DAY-13-14-REPORT.md)** | Week 2 end validation | ⚠️ Historical | Cache + healing validated |
| **[DAY-11-12-NOTES.md](DAY-11-12-NOTES.md)** | Week 2 mid-sprint notes | ⚠️ Historical | Integration progress |
| **[DAY-9-RESULTS.md](DAY-9-RESULTS.md)** | Day 9 initial SF testing | ⚠️ Historical | 0% PASS (blocker found) |
| **[CACHE-VALIDATION-DAY8.md](CACHE-VALIDATION-DAY8.md)** | Day 8 cache testing | ⚠️ Historical | Redis + Postgres validated |
| **[PRODUCTION-VALIDATION-v2.1.md](PRODUCTION-VALIDATION-v2.1.md)** | v2.1 production testing | ⚠️ Historical | Pre-v3.0 results |

---

## 📋 Implementation Plans

### Active Plans (v3.1s - Current)

| File | Purpose | Status | Timeline |
|------|---------|--------|----------|
| **[PACTS-v3.1s-IMPLEMENTATION.md](PACTS-v3.1s-IMPLEMENTATION.md)** | 🆕 v3.1s Universal Mode implementation | ✅ **IMPLEMENTED** | Phases 1-3 complete, ready for validation |
| **[WEEK-8-PHASE-A-HANDOFF.md](WEEK-8-PHASE-A-HANDOFF.md)** | Week 8 Phase A+B - EDR validation | ✅ Complete | ✅ 100% PASS - Production Ready |
| **[WEEK-4-7-VALIDATION-REPORT.md](WEEK-4-7-VALIDATION-REPORT.md)** | Week 4-7 results + roadmap | ✅ Reference | Week 8 baseline |

### Planning (Deferred)

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| **[EXECUTOR-INTELLIGENCE-CORE.md](EXECUTOR-INTELLIGENCE-CORE.md)** | Week 9 MVP - Top 3 tools | ⏸️ **DEFERRED** | Dialog Sentinel dropped (too complex for edge cases) |
| **[PHASE-C-INTELLIGENT-AGENT.md](PHASE-C-INTELLIGENT-AGENT.md)** | Phase C architecture spec | 📋 Planning | LSN + Runtime Adaptation (future work) |

### Completed Plans (Week 4-7)

| File | Purpose | Status | Outcome |
|------|---------|--------|---------|
| **[WEEK-4-LABEL-FIRST-IMPLEMENTATION.md](WEEK-4-LABEL-FIRST-IMPLEMENTATION.md)** | Label-first discovery strategy | ✅ **Complete** | 100% PASS, 62.5% stable selectors |
| **[DAY-9-12-ACTION-PLAN.md](DAY-9-12-ACTION-PLAN.md)** | Week 2-3 action items | ✅ Complete | Session-scoped cache, bypass |
| **[NEXT-STEPS-REALISTIC.md](NEXT-STEPS-REALISTIC.md)** | Realistic next steps | ⚠️ Outdated | Superseded by Week 4-7 |

### Roadmaps & Blueprints

| File | Purpose | Status | Version |
|------|---------|--------|---------|
| **[PACTS-v3.0-IMPLEMENTATION-PLAN.md](PACTS-v3.0-IMPLEMENTATION-PLAN.md)** | v3.0 implementation roadmap | ✅ Reference | v3.0 |

**v3.1s Roadmap** (Current):
- ✅ Phase 1: Stealth Mode (headless browser detection avoidance)
- ✅ Phase 2: Friendly CLI (`pacts test tests/` with auto-discovery)
- ✅ Phase 3: Data-Driven Execution (${var} templates + CSV/JSONL/YAML)
- 📋 Phase 4: QA Validation (GitHub, SPAs, auth flows ≥95% pass rate)

---

## 🔧 Troubleshooting & Fixes

### Known Issues & Solutions

| File | Purpose | Status | Issue |
|------|---------|--------|-------|
| **[WINDOWS-DOCKER-NETWORKING-ISSUE.md](WINDOWS-DOCKER-NETWORKING-ISSUE.md)** | Docker networking on Windows | ✅ Resolved | Host networking not supported |
| **[DEPENDENCY-RESOLUTION-SOLUTION.md](DEPENDENCY-RESOLUTION-SOLUTION.md)** | Poetry dependency conflicts | ✅ Resolved | Anthropic SDK + httpx versions |
| **[ANTHROPIC-SDK-FIX.md](ANTHROPIC-SDK-FIX.md)** | Anthropic SDK compatibility | ✅ Resolved | Version pinning solution |
| **[POETRY-SUCCESS-SUMMARY.md](POETRY-SUCCESS-SUMMARY.md)** | Poetry setup success | ✅ Reference | Migration from pip |

**Common Issues**: Check [WINDOWS-DOCKER-NETWORKING-ISSUE.md](WINDOWS-DOCKER-NETWORKING-ISSUE.md) for Docker troubleshooting.

---

## 📝 Session Notes & Summaries

### Recent Sessions (Week 3 - Nov 2025)

| File | Date | Purpose | Key Outcomes |
|------|------|---------|--------------|
| **[SESSION-SUMMARY-2025-11-03.md](SESSION-SUMMARY-2025-11-03.md)** | 2025-11-03 | Week 3 Day 15 session | Lightning validation, bypass implementation |
| **[SESSION-SUMMARY-2025-11-02.md](SESSION-SUMMARY-2025-11-02.md)** | 2025-11-02 | Week 3 session | Salesforce fixes, repo cleanup |
| **[V3.0-SESSION-SUMMARY.md](V3.0-SESSION-SUMMARY.md)** | 2025-11-02 | v3.0 kickoff session | Architecture decisions, Docker setup |
| **[DAY-8-9-COMPLETE-SUMMARY.md](DAY-8-9-COMPLETE-SUMMARY.md)** | 2025-11-03 | Day 8-9 summary | Cache validation, SF blocker found |

**Latest**: [SESSION-SUMMARY-2025-11-03.md](SESSION-SUMMARY-2025-11-03.md)

---

## 🗄️ Archive & Deprecated

### Historical Documentation

| File | Purpose | Status | Reason |
|------|---------|--------|--------|
| **[SALESFORCE-FIXES-SUMMARY.md](SALESFORCE-FIXES-SUMMARY.md)** | Pre-v3.0 SF fixes | 📦 Archived | Superseded by DAY-15 report |
| **[RELEASE-v1.2.md](RELEASE-v1.2.md)** | v1.2 release notes | 📦 Archived | Historical reference |
| **[REPO-CLEANUP-SUMMARY.md](REPO-CLEANUP-SUMMARY.md)** | Repo cleanup notes | 📦 Archived | Cleanup completed |

**Note**: Archived docs are kept for historical reference but are not actively maintained.

---

## 🔍 Quick Reference by Task

### I want to...

**...get started with PACTS**
- Read: [QUICK-START.md](QUICK-START.md)
- Then: [DOCKER-SETUP.md](DOCKER-SETUP.md)

**...understand the architecture**
- Read: [PACTS-TECHNICAL-SPEC-v2.1.md](PACTS-TECHNICAL-SPEC-v2.1.md)
- Then: [PACTS-COMPLETE-SPECIFICATION.md](PACTS-COMPLETE-SPECIFICATION.md)

**...see latest test results**
- Read: [WEEK-8-PHASE-A-HANDOFF.md](WEEK-8-PHASE-A-HANDOFF.md) (🆕 LATEST - Week 8 Phase A)
- Previous: [WEEK-4-7-VALIDATION-REPORT.md](WEEK-4-7-VALIDATION-REPORT.md) (Week 4-7)
- Historical: [DAY-15-LIGHTNING-VALIDATION.md](DAY-15-LIGHTNING-VALIDATION.md) (Week 3)

**...fix a Docker issue**
- Read: [WINDOWS-DOCKER-NETWORKING-ISSUE.md](WINDOWS-DOCKER-NETWORKING-ISSUE.md)
- Then: [DOCKER-SETUP.md](DOCKER-SETUP.md)

**...fix a dependency issue**
- Read: [DEPENDENCY-RESOLUTION-SOLUTION.md](DEPENDENCY-RESOLUTION-SOLUTION.md)
- Or: [ANTHROPIC-SDK-FIX.md](ANTHROPIC-SDK-FIX.md)

**...understand Week 8 Phase A (EDR)**
- Read: [WEEK-8-PHASE-A-HANDOFF.md](WEEK-8-PHASE-A-HANDOFF.md) (🆕 comprehensive validation)
- Focus: 8-tier discovery, runtime profiles, stable-only caching, universal readiness

**...understand Week 4-7 progress**
- Read: [WEEK-4-7-VALIDATION-REPORT.md](WEEK-4-7-VALIDATION-REPORT.md) (comprehensive report)
- Context: [DAY-15-LIGHTNING-VALIDATION.md](DAY-15-LIGHTNING-VALIDATION.md) (Week 3 baseline)

**...plan Phase B work**
- Read: [WEEK-8-PHASE-A-HANDOFF.md](WEEK-8-PHASE-A-HANDOFF.md) (see "Phase B Preview" section)
- Focus: Context awareness, planner cohesion, intelligent defaults

**...understand Week 9 Phase C (Dialog Sentinel)**
- Read: [api/WEEK-9-SENTINEL-VALIDATION.md](api/WEEK-9-SENTINEL-VALIDATION.md) (validation findings with false positive analysis)
- Implementation: [DIALOG-SENTINEL-POC.md](DIALOG-SENTINEL-POC.md) (POC summary)
- Results: [DIALOG-SENTINEL-POC-RESULTS.md](DIALOG-SENTINEL-POC-RESULTS.md) (test results)
- Focus: Auto-close error dialogs, false positive filtering, positive indicators

**...plan Phase C Track B (Executor Intelligence)**
- Read: [EXECUTOR-INTELLIGENCE-CORE.md](EXECUTOR-INTELLIGENCE-CORE.md) (Top 3 tools for Week 9 MVP)
- Architecture: [PHASE-C-INTELLIGENT-AGENT.md](PHASE-C-INTELLIGENT-AGENT.md) (complete Phase C spec)
- Focus: Dialog Sentinel, Grid Reader, Duplicate Disambiguator (Duplex)

---

## 📊 Documentation Statistics

**Total Files**: 40 markdown files
**Active (Root Level)**: 23 files + 1 api/ directory (1 file)
**Archived (archive/)**: 16 files
**Archive Categories**: 6 (week2, sessions, fixes, specs, releases, salesforce)

**Last Update**: 2025-11-08 (Week 9 Phase C - Dialog Sentinel POC validation)
**Next Review**: Week 9 Phase C (after Sentinel false positive fix)

---

## 🗂️ Archive Structure & API Documentation

**Locations**:
- `docs/archive/` - Historical documentation organized by category
- `docs/api/` - 🆕 API-level documentation and detailed validation reports

Historical documentation has been moved to the archive for reference. The archive is organized by category:

### Week 2 Reports
- ✅ [DAY-9-RESULTS.md](archive/week2/DAY-9-RESULTS.md) - Day 9 initial SF testing
- ✅ [DAY-11-12-NOTES.md](archive/week2/DAY-11-12-NOTES.md) - Week 2 mid-sprint notes
- ✅ [DAY-13-14-REPORT.md](archive/week2/DAY-13-14-REPORT.md) - Week 2 end validation
- ✅ [CACHE-VALIDATION-DAY8.md](archive/week2/CACHE-VALIDATION-DAY8.md) - Day 8 cache testing

### Session Summaries
- ✅ [SESSION-SUMMARY-2025-11-02.md](archive/sessions/SESSION-SUMMARY-2025-11-02.md)
- ✅ [SESSION-SUMMARY-2025-11-03.md](archive/sessions/SESSION-SUMMARY-2025-11-03.md)
- ✅ [DAY-8-9-COMPLETE-SUMMARY.md](archive/sessions/DAY-8-9-COMPLETE-SUMMARY.md)
- ✅ [V3.0-SESSION-SUMMARY.md](archive/sessions/V3.0-SESSION-SUMMARY.md)

### Fix Summaries
- ✅ [ANTHROPIC-SDK-FIX.md](archive/fixes/ANTHROPIC-SDK-FIX.md) - Anthropic SDK compatibility
- ✅ [POETRY-SUCCESS-SUMMARY.md](archive/fixes/POETRY-SUCCESS-SUMMARY.md) - Poetry setup
- ✅ [REPO-CLEANUP-SUMMARY.md](archive/fixes/REPO-CLEANUP-SUMMARY.md) - Repo cleanup notes

### Old Specifications
- ✅ [PACTS-Phase-1-Final-Blueprint-v3.5.md](archive/specs/PACTS-Phase-1-Final-Blueprint-v3.5.md)
- ✅ [PRODUCTION-VALIDATION-v2.1.md](archive/specs/PRODUCTION-VALIDATION-v2.1.md)

### Release Notes
- ✅ [RELEASE-v1.2.md](archive/releases/RELEASE-v1.2.md)

### Salesforce Historical
- ✅ [SALESFORCE-FIXES-SUMMARY.md](archive/salesforce/SALESFORCE-FIXES-SUMMARY.md)

### API Documentation (New - Week 9+)
- ✅ [WEEK-9-SENTINEL-VALIDATION.md](api/WEEK-9-SENTINEL-VALIDATION.md) - Week 9 Dialog Sentinel validation report

### Active Documentation (Root Level)

**Core Documentation**:
- `INDEX.md` (this file)
- `README.md` (project overview)
- `QUICK-START.md` (setup guide)
- `DOCKER-SETUP.md` (Docker environment)
- `PACTS-TECHNICAL-SPEC-v2.1.md` (technical reference)
- `PACTS-COMPLETE-SPECIFICATION.md` (feature spec)
- `PACTS-v3.0-IMPLEMENTATION-PLAN.md` (roadmap)

**Current Validation Reports** (Week 3+):
- `WEEK-8-PHASE-A-HANDOFF.md` (Week 8 Phase A+B - PRODUCTION READY)
- `WEEK-4-7-VALIDATION-REPORT.md` (Week 4-7 results)
- `WEEK-4-EXTENDED-VALIDATION.md` (Week 4 extended)
- `WEEK-4-LABEL-FIRST-IMPLEMENTATION.md` (Week 4 implementation)
- `DAY-15-LIGHTNING-VALIDATION.md` (Week 3 validation)
- `SALESFORCE-VALIDATION-REPORT.md` (Week 3 summary)
- `DAY-9-FINAL-RESULTS.md` (important blocker reference)

**Phase C - Executor Intelligence** (Week 9+):
- `EXECUTOR-INTELLIGENCE-CORE.md` (Week 9 MVP - Top 3 tools)
- `PHASE-C-INTELLIGENT-AGENT.md` (Complete Phase C architecture)
- `DIALOG-SENTINEL-POC.md` (Dialog Sentinel implementation)
- `DIALOG-SENTINEL-POC-RESULTS.md` (POC test results)

**Implementation Guides**:
- `EDR.md` (Enhanced Discovery & Reliability)
- `UNIVERSAL-DISCOVERY-GUIDE.md` (Discovery patterns)
- `WINDOWS-DOCKER-NETWORKING-ISSUE.md` (Windows Docker fix)
- `DEPENDENCY-RESOLUTION-SOLUTION.md` (Dependency resolution)
- `DAY-9-12-ACTION-PLAN.md` (Action plan)
- `NEXT-STEPS-REALISTIC.md` (Next steps)

**Benefits of Documentation Structure**:
- ✅ Active docs in root (easy to find - 23 core files)
- ✅ Historical docs preserved (searchable via archive/ - 16 files)
- ✅ API-level reports in dedicated directory (docs/api/)
- ✅ Clear separation (current vs archived vs detailed reports)
- ✅ Reduced clutter (40 total files, well-organized)

---

## 🎯 Maintenance Guidelines

### When to Update This Index

- **Weekly**: After major milestones (e.g., Week 3 completion)
- **On New Docs**: When creating new markdown files
- **On Archive**: When moving files to archive/
- **On Cleanup**: After deleting obsolete files

### How to Keep It Current

1. Update "Last Updated" date at top
2. Add new files to appropriate category
3. Mark completed items as archived
4. Update "Latest" links to current reports
5. Review "Recommended Cleanup" section

---

**Maintained by**: Claude Code
**Next Review**: Week 9 Phase C completion (after Dialog Sentinel, Grid Reader, Duplex)
**Questions?**: Refer to [README.md](README.md)

---

## 🚨 Critical Action Items (Week 9)

Based on [api/WEEK-9-SENTINEL-VALIDATION.md](api/WEEK-9-SENTINEL-VALIDATION.md):

1. **URGENT**: Fix Dialog Sentinel false positives
   - **Issue**: Incorrectly closes "New Account" modals
   - **Root Cause**: Pattern `r'required'` matches "* = Required Information" in legitimate forms
   - **Fix**: Add positive indicator filter to distinguish create forms from error dialogs
   - **File**: [backend/agents/dialog_sentinel.py](../backend/agents/dialog_sentinel.py)

2. **Test**: Re-validate with updated Sentinel
   - Run Salesforce Contact + Account creation test
   - Verify: "New Account" modal stays open, actual error dialogs are closed

3. **Document**: Update validation report with results
   - Update [api/WEEK-9-SENTINEL-VALIDATION.md](api/WEEK-9-SENTINEL-VALIDATION.md) with fix results
   - Add telemetry for false positive rate tracking
