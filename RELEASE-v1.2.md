# PACTS v1.2 - Production Validated Release

**Release Date**: 2025-11-01
**Status**: Production Ready
**Confidence Level**: HIGH

## Headline Achievement

100% Success Rate Across 6 Production Sites:
- Salesforce Lightning (NEW): Dialog scoping + HITL 2FA
- Wikipedia, GitHub, Amazon, eBay, SauceDemo (existing)
- 0 heal rounds average
- Pattern-based execution validated

## What's New

### Salesforce Lightning Support
- Dialog-scoped discovery for App Launcher navigation
- LAUNCHER_SEARCH pattern with auto-navigation detection
- Smart button disambiguation (filters tabs, close buttons)
- HITL support for 2FA/CAPTCHA

### Architectural Improvements
- Centralized step utilities (backend/runtime/step_utils.py)
- Enhanced URL navigation detection (networkidle + Lightning page types)
- Smart button disambiguation for common actions

### Production Deployment Kit
- .env.prod: Production environment template
- versions.txt: Pinned toolchain versions  
- GitHub Actions: CI/CD smoke tests workflow
- CHANGELOG.md: Semantic versioning
- docs/SALESFORCE-FIXES-SUMMARY.md: Technical documentation

## Critical Fixes

1. Dialog Scoping Bug #1: Field name mismatch (planner.py:74)
2. Dialog Scoping Bug #2: Field not propagated (planner.py:358)
3. LAUNCHER_SEARCH Timeout: Auto-navigation detection (executor.py:244-266)
4. Button Disambiguation: NOT_UNIQUE errors (discovery.py:260-303)

## Validation Results

| Site | Pattern | Steps | Success | Heal Rounds |
|------|---------|-------|---------|-------------|
| Wikipedia | Autocomplete | 3 | 100% | 0 |
| GitHub | Activator | 4 | 100% | 0 |
| Amazon | E-commerce | 5 | 100% | 0 |
| eBay | Autocomplete | 4 | 100% | 0 |
| SauceDemo | Regression | 6 | 100% | 0 |
| Salesforce | Dialog Scoping + HITL | 15 | 100% | 0 |

## KPIs

- Success Rate: 100% (6/6 sites)
- Heal Rounds: 0 average
- Execution Time: 1.9s average per step
- Pattern Coverage: autocomplete, activator, dialog scoping, HITL

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.prod backend/.env
# Edit backend/.env with your credentials
```

## Running Tests

```bash
# Wikipedia
python -m backend.cli.main test --req wikipedia_search

# Salesforce (with HITL 2FA)
python -m backend.cli.main test --req salesforce_full_hitl --headed --slow-mo 800
```

## Documentation

- Technical Deep-Dive: docs/SALESFORCE-FIXES-SUMMARY.md
- Changelog: CHANGELOG.md
- Version Pinning: versions.txt
- Production Config: .env.prod

## Next Steps (Optional)

High Priority:
1. Drift Canary: Nightly runs with drift detection
2. HITL Runbook: 1-pager for operators
3. Salesforce Patterns Guide: App Launcher, button disambiguation

Medium Priority:
4. MCP Phase-B: Action validation scaffolding
5. Salesforce Breadth: Opportunity + Case flows
6. Lower Confidence Scores: For disambiguated selectors

## Support

- Issues: https://github.com/debashishroy00/pacts/issues
- Discussions: https://github.com/debashishroy00/pacts/discussions
