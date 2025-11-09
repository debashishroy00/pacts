# PACTS v3.1s — VALIDATION PLAN (Phase 4a–4c)

Author: DR · Date: 2025‑11‑08 · Audience: Core Contributors (CC)
Objective: Raise pass rate from 40% → ≥ 75% in 1–2 weeks by hardening stealth, fixing hidden element activation, and improving non‑unique selector handling. Keep the system universal (no platform-specific hacks).

---

## Phase 4a — Stability Hotfix (this week)

### A. Stealth 2.0 Upgrade
Goal: Reduce anti‑bot detection (e.g., Stack Overflow /nocaptcha) without headed mode.

Deliverables
- Integrate advanced stealth patch
- Add human‑like timing & minimal mouse movement
- Add CAPTCHA detection flag

Implementation
1) Library
```bash
pip install playwright-stealth
```
2) Hook (backend/runtime/launch_stealth.py)
```python
from playwright_stealth import stealth_async

# after creating page
page = await ctx.new_page()
await stealth_async(page)  # canvas/fonts/plugins/webrtc spoofing

# tiny human signals (first page only)
await page.mouse.move(120, 160)
await page.wait_for_timeout(random.uniform(120, 380))
```
3) Telemetry additions
- `stealth_v=2`
- `blocked_headless` (0/1)
- `block_sig` (first blocking URL or DOM signature)

4) CAPTCHA detection (executor middleware)
- If URL contains `/nocaptcha` or DOM has `form[action*="captcha"]`:
  - mark `blocked_headless=1`
  - short-circuit run with status `blocked`
  - store screenshot + HTML

Acceptance
- Stack Overflow: still allowed to fail, but must mark `blocked` fast (no wasted heals).

---

### B. Hidden Element Activation (GitHub & similar UIs)
Goal: When discovery returns a hidden input, activate the UI first.

Deliverables
- Auto‑activation for collapsed search bars or popovers
- Visibility guard before fill

Implementation (executor fill step)
```python
loc = page.locator('input[name="query-builder-test"]')
if not await loc.is_visible():
    # try common activators
    act = page.get_by_role('button', name='Search').first
    if await act.is_visible():
        await act.click()
        await page.wait_for_timeout(150)  # small settle
    # re-check
    if not await loc.is_visible():
        raise StepBlocked('element_hidden')

await loc.fill(value)
```
Acceptance
- GitHub search test passes end‑to‑end without test spec changes.

---

### C. Non‑Unique Selector Handling (YouTube & filter chips)
Goal: When role/name is non‑unique, choose a stable text‑based or nth fallback.

Deliverables
- Text‑based fallback: `button:has-text("<label>")`
- nth fallback when text is duplicated
- Uniqueness check moved before action

Implementation (discovery fallback)
```python
if not unique(selector):
    # prefer role+name via Playwright API
    alt = page.get_by_role('button', name=label)
    if await alt.count() == 1:
        return alt
    # text CSS fallback
    alt = f'button:has-text("{label}")'
    if unique(alt):
        return alt
    # last resort: nth(0)
    return f'button:has-text("{label}"):nth(0)'
```
Acceptance
- YouTube filter “Video” chip is clicked reliably; test passes.

---

## Phase 4b — Validation Re‑Run

Test Suites (under tests/validation/)
- `static_sites.yaml` (wikipedia, docs.python.org)
- `spa_sites.yaml` (react demo, angular playground)
- `auth_flows.yaml` (GitHub, WordPress) — uses @env secrets
- `multi_dataset.yaml` + `users.csv`

Command
```bash
pacts test tests/validation/ --parallel=3
```

Success Criteria
| Metric | Target |
|-------|--------|
| Pass rate | ≥ 75 % overall |
| Stealth detections | < 10 % |
| Avg step duration | < 2 s |
| Retry rate | < 5 % |

Artifacts
- `runs/validation/<suite>/metrics_summary.json`
- `runs/validation/<suite>/junit_report.xml`
- `docs/PACTS-v3.1s-VALIDATION.md` (aggregate report)

---

## Phase 4c — Incremental Refinements (optional, if needed)

1) Human pacing on first page of each site
```python
await page.wait_for_timeout(random.uniform(120, 320))
await page.mouse.wheel(0, 200)
```
2) Viewport jitter (keep reasonable)
- width: 1320–1420 · height: 740–820
3) Profile rotation
- rotate 2–3 profile dirs to avoid exact fingerprint reuse
4) Hard block classifier
- quick heuristic to skip healing when blocked by CAPTCHA

---

## Reporting Template (paste into docs/PACTS-v3.1s-VALIDATION.md)

### Summary
- Overall pass rate: X % (Y/Z)
- Detections: A %
- Avg step: N.nn s
- Retries: R %

### By Suite
| Suite | Passed/Total | Notes |
|------|---------------|-------|
| static_sites |  |  |
| spa_sites |  |  |
| auth_flows |  |  |
| multi_dataset |  |  |

### Top Failure Signatures
1) `blocked(nocaptcha)` — count
2) `element_hidden` — count
3) `not_unique(selector)` — count

### Actions
- [ ] Stealth tuning
- [ ] Activation rule extended
- [ ] Discovery nth/text fallback extended

---

## Release Gate

Tag the release when all criteria are met:
```bash
git tag v3.1s-validation-pass
git push --tags
```
Update `docs/INDEX.md` with the “v3.1s Validated” section.

---

## Appendix — Env & Flags

```
PACTS_STEALTH=true
PACTS_PERSISTENT_PROFILES=true
PACTS_PROFILE_DIR=runs/userdata
PACTS_TZ=America/New_York
PACTS_LOCALE=en-US
PACTS_PARALLEL=3
```

Notes
- Keep everything headless/Docker‑friendly.
- No platform‑specific branches; fixes must be universal.
- If a site still blocks (e.g., Stack Overflow), mark `blocked` fast and move on.
