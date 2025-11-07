Engineering Decision Record — Universal Discovery & Execution Strategy

Version: v1.0
Date: 2025-11-06
Owner: Debashish Roy
Implementation Lead: CC
Branch: main
Scope: Week 8 – Universal Discovery & Planner Cohesion

🎯 1. Decision Summary

PACTS will evolve from a Salesforce-tuned system to a universal web testing engine that works seamlessly across any web application (with optional desktop extensibility).

Warm-run perfection for dynamic SPAs (like Salesforce Lightning) is no longer a quality gate.
The new goal: 100% cold-run robustness and consistent user experience across all web platforms.

🧩 2. Key Architectural Decisions
Area	Decision	Rationale
Locator Strategy	Universal discovery order: aria-* → name → placeholder → label[for] → visible text (role+name) → data-* → id/class	Works across all web apps; ignores framework-specific volatility
Selector Policy	Only stable selectors (attribute-based) are cached. Volatile selectors are single-use.	Prevents cache pollution across dynamic SPAs
Profiles	Introduce Static Web and Dynamic SPA runtime profiles (auto-detected + user override).	Simplifies tuning (timeouts, retries, readiness, caching)
Scope Handling	Scopes (within) become first-class: discovery always resolves container first; planner auto-inserts “open” actions if scope missing.	Generalizes modal, dialog, dropdown, launcher patterns
Readiness Gate	Every step (discovery + execution) performs 3-stage readiness: (1) DOM idle, (2) element visible & enabled, (3) optional app readiness hook.	Works generically for static + dynamic apps
Healing Behavior	One retry tier per discovery level; no duplicate retries. Healing marks fallback selector as stable if successful.	Improves reliability, avoids infinite loops
Planner Enrichment	Generic UX rules (modal, dropdown, tab) apply automatically — user never writes “within” manually.	Removes cognitive load on testers
Warm-Run Policy	Warm-run flakes on highly dynamic SPAs are tolerated and logged but not blockers.	Focuses effort where ROI is highest (cold-run UX)
🧠 3. Implementation Phases (for CC)
Phase A — Universal Discovery Core (3–4 days)

Goal: Make discovery & healing consistent across any web app.

Tasks

Modify discovery.py:

Implement the universal locator priority:

STRATEGIES = [
    try_aria_label, try_aria_placeholder,
    try_name_attr, try_placeholder_attr,
    try_label_for, try_role_name,
    try_data_attr, try_id_class
]


Mark each selector with stable=True or stable=False.

Return {selector, strategy, stable} to caller.

Skip caching if stable=False.

Update selector_cache.py:

Cache only if stable=True.

Add volatile_count metric to logs.

Extend cache key with profile (STATIC/DYNAMIC).

Add runtime_profile.py (NEW):

Detect profile automatically:

if "lightning.force.com" in url or "react" in script_tags:
    return "DYNAMIC"
return "STATIC"


Export get_profile(url) utility.

Update .env:

PACTS_PROFILE_DEFAULT=STATIC
PACTS_PROFILE_OVERRIDE=   # optional


Update executor.py:

Insert readiness gate before every action:

await page.wait_for_load_state("networkidle")
await page.wait_for_selector(selector, state="visible", timeout=profile_timeout)
if hasattr(window, "__APP_READY__"):
    await page.evaluate("__APP_READY__()")


Update oracle_healer.py:

Enforce tier bumping (never retry same selector).

Mark successful fallback as stable=True.

Add [HEAL] upgraded selector → marked stable log.

Testing:

Run test suite:

Wikipedia Search (static)

React To-Do app (SPA)

Salesforce Opportunity create (SPA)

Validate: 3/3 cold runs PASS across all, ≤1 heal per test.

Phase B — Context & Planner Cohesion (3 days)

Goal: Unify “within” handling and contextual discovery.

Tasks

Update planner.py:

Add apply_ux_patterns() for generic modal/dialog/dropdown rules.

Example rules:

open_modal → next steps get within="<modal name>"

click tab → wait for tab content

click dropdown → add wait="listbox"

Auto-insert wait + within if missing.

Update salesforce_helpers.py:

Rename to scope_helpers.py (generic).

Add resolve_container(name) → finds modal/dialog by role.

Export ensure_scope_ready(context).

Update discovery.py:

Support scoped discovery:

if context:
    container = await resolve_container(context)
    locator = container.locator(selector)


Log [SCOPE] ✅ Found container={context}.

Testing:

Test Salesforce App Launcher (dialog)

Test e-commerce checkout modal

Test generic dropdown select

Expect: 3/3 cold runs PASS, scopes resolved dynamically.

Phase C — Observability & Documentation (2 days)

Add unified log format:

[DISCOVERY] strategy=aria-label stable=✓

[SCOPE] resolved dialog="Login Modal"

[READINESS] toolbar interactive

[HEAL] upgraded selector stable=✓

[PROFILE] using=DYNAMIC (SPA detected)

Add docs/UNIVERSAL-DISCOVERY-GUIDE.md:

Document strategy order, profiles, caching policy, and known trade-offs.

Final smoke tests:

Salesforce (SPA), Wikipedia (static), GitHub (SPA), Notion (React).

Validate: All cold runs PASS, ≤1 heal, logs clean.

📊 4. Success Metrics
Metric	Target	Measurement
Cold-run pass rate	≥95% across all web apps	Automated test logs
Warm-run recovery rate	≥80% (if cache hit invalid)	Healer metrics
Avg. heal rounds	≤1	Runtime logs
Selector stability ratio	≥60% stable selectors	Discovery logs
Scope resolution success	≥90%	[SCOPE] logs
User-written hints required	0	Planner inserts automatically
🔒 5. Risks & Mitigations
Risk	Mitigation
Over-engineering warm-run caching	Ignore volatile selectors in cache
Readiness wait inflation	Use profile-based timeout caps
Cross-site selector conflicts	Include domain in cache key
SPA frameworks evolving	Make discovery strategy extensible via YAML config
🧾 6. Deliverables Checklist (for CC)

 backend/runtime/discovery.py — universal strategy

 backend/storage/selector_cache.py — stable-only caching

 backend/runtime/runtime_profile.py — new module

 backend/agents/executor.py — readiness gate

 backend/agents/oracle_healer.py — tiered healing

 backend/agents/planner.py — UX rule enrichment

 backend/runtime/scope_helpers.py — scoped discovery utils

 .env — profile toggles

 docs/UNIVERSAL-DISCOVERY-GUIDE.md — documentation

 Validation runs (4 apps, 3 runs each)

 Commit with message:

feat: universal discovery + scoped planner cohesion (Week 8 EDR)

🏁 7. Expected Outcome

After executing this EDR, PACTS will:

Reliably discover and interact with any web app, static or dynamic

Require zero user-authored selectors or hints

Pass all cold-run tests with ≥95% consistency

Be ready for desktop adapter integration (via same planner model)