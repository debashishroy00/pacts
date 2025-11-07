Universal Discovery Guide

Version: 1.0
Date: 2025-11-06
Applies to: PACTS Universal Discovery & Planner Cohesion Architecture (Week 8 EDR)

🧭 1. Purpose

PACTS now supports all web applications, not just Salesforce.
This guide explains how the discovery engine, cache, planner, and healer work together to locate and interact with elements across any modern UI framework — from static HTML pages to dynamic SPAs like Salesforce, GitHub, or React Admin apps.

🔍 2. How PACTS Finds Elements
2.1 Universal Discovery Order

PACTS discovers elements using a stability-first hierarchy.
Each discovered selector is tagged with a stable or volatile flag and stored accordingly.

Priority	Strategy	Example	Stability
1	aria-label, aria-labelledby	input[aria-label="Email"]	✅ Stable
2	aria-placeholder	input[aria-placeholder="Search"]	✅ Stable
3	name attribute	input[name="Username"]	✅ Stable
4	placeholder attribute	input[placeholder="Enter Password"]	✅ Stable
5	<label for> proximity	label[for="email"] + input	✅ Stable
6	Visible text / role-name	role=button[name*="Submit"i]	⚠ Volatile
7	data-* attribute	*[data-testid="login-btn"]	✅ Stable
8	id / class	#input-390	⚠ Volatile

Selectors from tiers 1-5 are cached; tiers 6-8 are single-use only.

2.2 Stability Logic

Stable selector = based on meaningful user-visible or semantic attributes.

Volatile selector = derived from framework-generated IDs or ephemeral role+text patterns.

Cache writes occur only when stable=True.

Logs will show:

[CACHE] 💾 SAVED selector=input[name="Email"] strategy=name stable=✓
[CACHE] ⏩ SKIPPED selector=#input-390 stable=⚠

⚙️ 3. Runtime Profiles

PACTS adapts automatically to the target application through runtime profiles.

Profile	Typical Sites	Behavior
STATIC	Classic HTML, CMS, admin portals	Caches all stable selectors, short waits (1–2 s), single retry
DYNAMIC (SPA)	Salesforce, React, Angular, Vue	Caches stable selectors only, longer waits (3–6 s), multi-stage readiness & retries

Auto-detection runs on page load:

if "lightning.force.com" in url or "react" in script_tags:
    profile = "DYNAMIC"
else:
    profile = "STATIC"


Override via .env:

PACTS_PROFILE_DEFAULT=STATIC
PACTS_PROFILE_OVERRIDE=DYNAMIC


Logs confirm profile:

[PROFILE] using=DYNAMIC (SPA detected)

🕹️ 4. Readiness Gates

Every action (discovery + execution) now performs three universal readiness checks:

DOM Idle:
Wait until network/animation quiet:
await page.wait_for_load_state("networkidle")

Element Ready:
Ensure visible + enabled:
await page.wait_for_selector(selector, state="visible")

App Ready Hook:
Optional call to window.__APP_READY__() if defined by the app.

This guarantees the element is interactable across both static and dynamic frameworks.

🧩 5. Context & Scope
5.1 Scoping Principle

Whenever a user action occurs within a container (modal, launcher, dropdown, tab),
PACTS automatically resolves that container before performing the action.

Example log flow:

[Planner] 🎯 Applied UX rule 'open_modal_scope'
[SCOPE] ✅ Found container="Login Modal"
[DISCOVERY] using scoped locator input[name="Username"]


If the container is not open yet, the planner automatically inserts the open action and wait.

5.2 Typical Scopes Supported

Modals / Dialogs (role="dialog")

App Launchers / Drawers

Dropdowns / Listboxes

Tabs / Accordion Panels

🔄 6. Healing Workflow

When an element fails:

Tier bump: Move to next strategy tier.

Skip duplicates: Never retry identical selector.

Mark success: If a fallback works, mark as stable=True and write to cache.

Report cause: [HEAL] upgraded selector stable=✓ (was placeholder)

Healer never loops infinitely; max 5 rounds by default.

🧠 7. Planner Intelligence

The planner uses UX patterns to understand context and timing.
Examples:

Rule	Trigger	Injected Behavior
open_modal_scope	Click on “Login” button	Adds wait="dialog", then scopes next steps
dropdown_selection	Click on dropdown	Adds wait="listbox", within="Dropdown"
salesforce_lightning_new_on_list	Click “New” on Lightning list	Adds post_wait_ms=1500 for hydration
tab_navigation	Click on tab header	Adds wait="tabpanel"

Users never write these hints manually; the planner handles it.

🪶 8. Observability

Every action emits structured logs for traceability:

[PROFILE] using=STATIC
[DISCOVERY] strategy=aria-label stable=✓ selector=input[aria-label="Email"]
[SCOPE] resolved container="App Launcher"
[READINESS] page interactive
[HEAL] upgraded selector stable=✓


Developers can filter logs by tag for RCA and metrics.

✅ 9. What Users Need to Know

You never write selectors.
Use natural language steps only.

Cold runs are the gold standard.
Warm-run cache reuse is opportunistic; cold-run reliability is guaranteed.

Scopes happen automatically.
PACTS understands modals, drawers, and dropdowns through UX rules.

Profiles handle performance.
Static apps run fast; dynamic apps wait intelligently.

🧾 10. Quick Reference Checklist
Task	Where	Log Tag
Discovery result stable	discovery.py	[DISCOVERY]
Cache write	selector_cache.py	[CACHE]
Readiness check	executor.py	[READINESS]
Scope resolved	scope_helpers.py	[SCOPE]
Heal fallback	oracle_healer.py	[HEAL]
Profile detected	runtime_profile.py	[PROFILE]
🚀 11. Validation Targets
App	Profile	Expected Result
Wikipedia	Static	3/3 runs PASS, 0 heals
React To-Do	Dynamic	3/3 cold PASS, ≤1 heal
Salesforce Opportunity	Dynamic	3/3 cold PASS, ≤1 heal
GitHub Issues New	Dynamic	3/3 cold PASS
🏁 12. Future Extensions
Area	Direction
Desktop Adapter	Implement ElementFinder, ActionPerformer, ReadinessProbe interfaces for WinAppDriver/pywinauto.
Visual Heuristics	Optional Vision API for image/text-based element matching.
Locator Schema Config	YAML-based override for enterprise clients (custom data-attrs).
🔒 Document Control

Maintainer: CC
Approved By: Debashish Roy
Next Review: After Week 10 integration tests