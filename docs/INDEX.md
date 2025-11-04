# PACTS v3.0 - Documentation Index

**Last Updated**: 2025-11-03
**Purpose**: Master index for all PACTS documentation

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
| **[QUICK-START.md](QUICK-START.md)** | Fast setup guide (5 minutes) | ✅ Current | 2025-11-02 |
| **[DOCKER-SETUP.md](DOCKER-SETUP.md)** | Docker environment setup | ✅ Current | 2025-11-02 |
| **[README.md](README.md)** | Project overview | ✅ Current | 2025-11-02 |

**Start Here**: If you're new to PACTS, read [QUICK-START.md](QUICK-START.md) first.

---

## 📐 Technical Specifications

### Architecture & Design

| File | Purpose | Status | Version |
|------|---------|--------|---------|
| **[PACTS-TECHNICAL-SPEC-v2.1.md](PACTS-TECHNICAL-SPEC-v2.1.md)** | Complete technical specification | ✅ Current | v2.1 |
| **[PACTS-COMPLETE-SPECIFICATION.md](PACTS-COMPLETE-SPECIFICATION.md)** | Comprehensive feature spec | ✅ Current | v3.0 |
| **[PACTS-Phase-1-Final-Blueprint-v3.5.md](PACTS-Phase-1-Final-Blueprint-v3.5.md)** | Phase 1 architecture blueprint | ⚠️ Historical | v3.5 (Phase 1) |

**Read This**: [PACTS-TECHNICAL-SPEC-v2.1.md](PACTS-TECHNICAL-SPEC-v2.1.md) is the authoritative technical reference.

---

## ✅ Validation & Testing Reports

### Salesforce Lightning Testing (Week 3 - Current)

| File | Purpose | Status | Key Findings |
|------|---------|--------|--------------|
| **[DAY-15-LIGHTNING-VALIDATION.md](DAY-15-LIGHTNING-VALIDATION.md)** | Week 3 comprehensive validation | ✅ **Current** | 100% PASS (Phase 2a bypass) |
| **[SALESFORCE-VALIDATION-REPORT.md](SALESFORCE-VALIDATION-REPORT.md)** | Standalone validation summary | ✅ Current | Session-scoped cache + bypass |
| **[DAY-9-FINAL-RESULTS.md](DAY-9-FINAL-RESULTS.md)** | Day 9 Lightning blocker findings | ✅ Reference | "New" button timeout identified |

**Latest Results**: [DAY-15-LIGHTNING-VALIDATION.md](DAY-15-LIGHTNING-VALIDATION.md) - 100% PASS with Phase 2a bypass

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

### Active Plans (Week 4)

| File | Purpose | Status | Timeline |
|------|---------|--------|----------|
| **[WEEK-4-LABEL-FIRST-IMPLEMENTATION.md](WEEK-4-LABEL-FIRST-IMPLEMENTATION.md)** | Label-first discovery strategy | 📋 **Ready** | Week 4 (1-2 days) |
| **[DAY-9-12-ACTION-PLAN.md](DAY-9-12-ACTION-PLAN.md)** | Week 2-3 action items | ✅ Complete | Week 2-3 |
| **[NEXT-STEPS-REALISTIC.md](NEXT-STEPS-REALISTIC.md)** | Realistic next steps | ⚠️ Outdated | Week 2 |

### Roadmaps & Blueprints

| File | Purpose | Status | Version |
|------|---------|--------|---------|
| **[PACTS-v3.0-IMPLEMENTATION-PLAN.md](PACTS-v3.0-IMPLEMENTATION-PLAN.md)** | v3.0 implementation roadmap | ✅ Reference | v3.0 |

**Week 4 Plan**: Label-first discovery strategy (see [DAY-15-LIGHTNING-VALIDATION.md](DAY-15-LIGHTNING-VALIDATION.md) roadmap section)

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
- Read: [DAY-15-LIGHTNING-VALIDATION.md](DAY-15-LIGHTNING-VALIDATION.md)
- Summary: [SALESFORCE-VALIDATION-REPORT.md](SALESFORCE-VALIDATION-REPORT.md)

**...fix a Docker issue**
- Read: [WINDOWS-DOCKER-NETWORKING-ISSUE.md](WINDOWS-DOCKER-NETWORKING-ISSUE.md)
- Then: [DOCKER-SETUP.md](DOCKER-SETUP.md)

**...fix a dependency issue**
- Read: [DEPENDENCY-RESOLUTION-SOLUTION.md](DEPENDENCY-RESOLUTION-SOLUTION.md)
- Or: [ANTHROPIC-SDK-FIX.md](ANTHROPIC-SDK-FIX.md)

**...understand Week 3 progress**
- Read: [DAY-15-LIGHTNING-VALIDATION.md](DAY-15-LIGHTNING-VALIDATION.md)
- Context: [DAY-9-FINAL-RESULTS.md](DAY-9-FINAL-RESULTS.md) (Day 9 blocker)

**...plan Week 4 work**
- Read: [WEEK-4-LABEL-FIRST-IMPLEMENTATION.md](WEEK-4-LABEL-FIRST-IMPLEMENTATION.md) (detailed plan)
- Summary: Week 4 Roadmap in [DAY-15-LIGHTNING-VALIDATION.md](DAY-15-LIGHTNING-VALIDATION.md#week-4-roadmap-label-first-strategy)

---

## 📊 Documentation Statistics

**Total Files**: 28 markdown files
**Active (Current)**: 8 files
**Reference (Historical)**: 12 files
**Archived (Deprecated)**: 8 files

**Last Cleanup**: 2025-11-03
**Next Review**: Week 4 (after label-first implementation)

---

## 🗂️ Recommended Cleanup Actions

### Files to Archive (move to `docs/archive/`)

1. **Day 9-14 Reports** (superseded by DAY-15):
   - `DAY-9-RESULTS.md` → `archive/week2/DAY-9-RESULTS.md`
   - `DAY-11-12-NOTES.md` → `archive/week2/DAY-11-12-NOTES.md`
   - `DAY-13-14-REPORT.md` → `archive/week2/DAY-13-14-REPORT.md`
   - `CACHE-VALIDATION-DAY8.md` → `archive/week2/CACHE-VALIDATION-DAY8.md`

2. **Session Summaries** (consolidated):
   - `SESSION-SUMMARY-2025-11-02.md` → `archive/sessions/SESSION-SUMMARY-2025-11-02.md`
   - `DAY-8-9-COMPLETE-SUMMARY.md` → `archive/sessions/DAY-8-9-COMPLETE-SUMMARY.md`
   - `V3.0-SESSION-SUMMARY.md` → `archive/sessions/V3.0-SESSION-SUMMARY.md`

3. **Troubleshooting (resolved)**:
   - `POETRY-SUCCESS-SUMMARY.md` → `archive/fixes/POETRY-SUCCESS-SUMMARY.md`
   - `REPO-CLEANUP-SUMMARY.md` → `archive/fixes/REPO-CLEANUP-SUMMARY.md`

4. **Old Specs** (superseded):
   - `PACTS-Phase-1-Final-Blueprint-v3.5.md` → `archive/specs/PACTS-Phase-1-Final-Blueprint-v3.5.md`
   - `PRODUCTION-VALIDATION-v2.1.md` → `archive/specs/PRODUCTION-VALIDATION-v2.1.md`
   - `RELEASE-v1.2.md` → `archive/releases/RELEASE-v1.2.md`
   - `SALESFORCE-FIXES-SUMMARY.md` → `archive/salesforce/SALESFORCE-FIXES-SUMMARY.md`

### Files to Keep (Active)

**Core Documentation** (keep in `docs/`):
- `INDEX.md` (this file)
- `README.md`
- `QUICK-START.md`
- `DOCKER-SETUP.md`
- `PACTS-TECHNICAL-SPEC-v2.1.md`
- `PACTS-COMPLETE-SPECIFICATION.md`
- `PACTS-v3.0-IMPLEMENTATION-PLAN.md`
- `DAY-15-LIGHTNING-VALIDATION.md` (latest validation)
- `SALESFORCE-VALIDATION-REPORT.md` (latest validation)
- `DAY-9-FINAL-RESULTS.md` (important blocker reference)
- `SESSION-SUMMARY-2025-11-03.md` (latest session)

**Troubleshooting** (keep in `docs/`):
- `WINDOWS-DOCKER-NETWORKING-ISSUE.md`
- `DEPENDENCY-RESOLUTION-SOLUTION.md`
- `ANTHROPIC-SDK-FIX.md`

**Action Plans** (keep in `docs/`):
- `DAY-9-12-ACTION-PLAN.md` (partially complete)
- `NEXT-STEPS-REALISTIC.md` (update for Week 4)

---

## 📦 Proposed Archive Structure

```
docs/
├── INDEX.md (this file)
├── README.md
├── QUICK-START.md
├── DOCKER-SETUP.md
├── PACTS-TECHNICAL-SPEC-v2.1.md
├── PACTS-COMPLETE-SPECIFICATION.md
├── PACTS-v3.0-IMPLEMENTATION-PLAN.md
├── DAY-15-LIGHTNING-VALIDATION.md
├── SALESFORCE-VALIDATION-REPORT.md
├── DAY-9-FINAL-RESULTS.md
├── SESSION-SUMMARY-2025-11-03.md
├── DAY-9-12-ACTION-PLAN.md
├── NEXT-STEPS-REALISTIC.md
├── WINDOWS-DOCKER-NETWORKING-ISSUE.md
├── DEPENDENCY-RESOLUTION-SOLUTION.md
├── ANTHROPIC-SDK-FIX.md
│
└── archive/
    ├── week2/
    │   ├── DAY-9-RESULTS.md
    │   ├── DAY-11-12-NOTES.md
    │   ├── DAY-13-14-REPORT.md
    │   └── CACHE-VALIDATION-DAY8.md
    ├── sessions/
    │   ├── SESSION-SUMMARY-2025-11-02.md
    │   ├── DAY-8-9-COMPLETE-SUMMARY.md
    │   └── V3.0-SESSION-SUMMARY.md
    ├── fixes/
    │   ├── POETRY-SUCCESS-SUMMARY.md
    │   └── REPO-CLEANUP-SUMMARY.md
    ├── specs/
    │   ├── PACTS-Phase-1-Final-Blueprint-v3.5.md
    │   └── PRODUCTION-VALIDATION-v2.1.md
    ├── releases/
    │   └── RELEASE-v1.2.md
    └── salesforce/
        └── SALESFORCE-FIXES-SUMMARY.md
```

**Benefits**:
- Active docs in root (easy to find)
- Historical docs preserved (searchable)
- Clear separation (current vs archived)
- Reduced clutter (14 active vs 28 total)

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
**Next Review**: Week 4 (after label-first implementation)
**Questions?**: Refer to [README.md](README.md)
