# Week 4 - Label-First Discovery Strategy

**Date**: 2025-11-04 (Planned)
**Goal**: Eliminate bypass toggle with stable, attribute-based selectors
**Status**: 📋 Ready for Implementation

---

## 🎯 Objective

**Problem**: Lightning forms generate new IDs on every navigation, requiring cache bypass for 100% PASS.

**Solution**: Prioritize stable attributes (`aria-label`, `name`, `placeholder`) over volatile IDs.

**Outcome**: Cache works on warm runs without bypass → faster execution, no healing.

---

## 📋 Scope

### What Changes

1. **Discovery Strategy Order** (global, feature-flagged)
   - **New Priority**: `aria-label` → `name` → `placeholder` → `label[@for]` → `role+name` → `id` (last resort)
   - **Old Priority**: `label[@for]` → `placeholder` → `role+name` → `id`

2. **Selector Shape** (what we cache)
   - **Prefer**: `input[aria-label="Opportunity Name"]` (stable)
   - **Avoid**: `#input-390` (volatile)
   - **Allow**: `role=button[name*="Save"i]` (stable role+name)

3. **Cache Policy** (write/read filters)
   - **Block**: Pure ID selectors from cache writes (when `PACTS_ALLOW_ID_CACHE=false`)
   - **Tag**: Selectors with `stable: true/false` based on strategy
   - **Prefer**: Stable entries on cache reads

4. **Rollout Safety**
   - **Feature Flag**: `PACTS_LABEL_FIRST=true|false` (default `false` initially)
   - **Safety Valve**: Keep `PACTS_SF_BYPASS_FORM_CACHE` as emergency rollback

---

## 🔧 Implementation Tasks

### File 1: `backend/agents/pom_builder.py`

**Changes**:
1. Add new discovery pipeline with label-first order
2. Produce `canonical_selector` (attribute form when available)
3. Guard new behavior with `PACTS_LABEL_FIRST` flag

**New Discovery Order**:
```python
# Week 4: Label-first discovery pipeline
discovery_strategies = [
    try_by_aria_label,      # NEW: input[aria-label="Opportunity Name"]
    try_by_name,            # NEW: input[name="opportunityName"]
    try_by_placeholder,     # ELEVATED: input[placeholder*="Enter name"]
    try_by_label_for,       # EXISTING: <label for="..."> → #id
    try_by_role_name,       # EXISTING: role=button[name*="Save"]
    try_by_id,              # DEMOTED: #input-390 (last resort)
]
```

**Pseudo-code**:
```python
async def discover_selector(page, element_text, action):
    label_first_enabled = os.getenv("PACTS_LABEL_FIRST", "false").lower() in ("1", "true")

    if label_first_enabled:
        # New pipeline
        for strategy in [try_aria_label, try_name, try_placeholder, try_label_for, try_role_name, try_id]:
            result = await strategy(page, element_text, action)
            if result:
                result["stable"] = strategy not in [try_id]  # Tag ID-based as unstable
                return result
    else:
        # Old pipeline (current behavior)
        return await legacy_discovery(page, element_text, action)
```

**Lines to Modify**: Discovery section (~lines 50-120)

---

### File 2: `backend/runtime/salesforce_helpers.py`

**Changes**:
1. Add `get_accessible_name(element)` helper
2. Add `build_attr_selector(element)` helper
3. Reuse existing Lightning readiness (no extra waits)

**New Functions**:
```python
async def get_accessible_name(element) -> Optional[str]:
    """
    Get accessible name (aria-label, aria-labelledby, or label text).
    Week 4: Used for stable selector discovery.
    """
    # Try aria-label
    aria_label = await element.get_attribute("aria-label")
    if aria_label:
        return aria_label.strip()

    # Try aria-labelledby
    labelledby_id = await element.get_attribute("aria-labelledby")
    if labelledby_id:
        # Fetch label element text
        pass

    # Try associated <label>
    element_id = await element.get_attribute("id")
    if element_id:
        label = await element.page.locator(f'label[for="{element_id}"]').first
        if await label.is_visible():
            return await label.inner_text()

    return None


async def build_attr_selector(element) -> Optional[str]:
    """
    Build attribute-based selector (avoid IDs).
    Week 4: Produces stable, cross-navigation selectors.

    Priority:
    1. aria-label
    2. name attribute
    3. placeholder
    4. role + name
    5. None (caller falls back to ID)
    """
    # Try aria-label
    aria_label = await element.get_attribute("aria-label")
    if aria_label:
        tag = await element.evaluate("el => el.tagName.toLowerCase()")
        return f'{tag}[aria-label="{aria_label}"]'

    # Try name attribute
    name = await element.get_attribute("name")
    if name:
        tag = await element.evaluate("el => el.tagName.toLowerCase()")
        return f'{tag}[name="{name}"]'

    # Try placeholder
    placeholder = await element.get_attribute("placeholder")
    if placeholder:
        return f'input[placeholder*="{placeholder}"i]'

    # Try role + accessible name
    role = await element.get_attribute("role")
    accessible_name = await get_accessible_name(element)
    if role and accessible_name:
        return f'role={role}[name*="{accessible_name}"i]'

    return None  # Caller can fall back to ID
```

**Lines to Add**: After `is_lightning_form_url()` (~line 357)

---

### File 3: `backend/storage/selector_cache.py`

**Changes**:
1. Add `stable` field to cached records
2. Block pure ID writes when `PACTS_ALLOW_ID_CACHE=false`
3. Prefer stable entries on cache reads
4. Add telemetry: `strategy`, `stable`, `unstable-hit`

**Updated Save Method**:
```python
async def save_selector(
    self, url: str, element: str, selector: str, confidence: float, strategy: str, context=None
) -> None:
    """
    Save selector to dual-layer cache.
    Week 4: Add stability tagging and ID-write veto.
    """
    allow_id_cache = os.getenv("PACTS_ALLOW_ID_CACHE", "true").lower() in ("1", "true")

    # Check if selector is pure ID
    is_pure_id = selector.startswith("#") and " " not in selector

    # Determine stability
    stable = strategy not in ["id", "label"]  # ID and label-for (produces IDs) are unstable

    # Veto pure ID writes if disabled
    if is_pure_id and not allow_id_cache and not stable:
        logger.info(f"[CACHE][VETO] Blocking unstable ID write: {selector} (strategy: {strategy})")
        return  # Skip cache write

    # Add metadata
    metadata = {
        "strategy": strategy,
        "stable": stable,
        "confidence": confidence,
    }

    # Save to Postgres with metadata
    await self._save_to_postgres(url, element, selector, confidence, strategy, metadata)

    # Warm Redis cache
    await self._save_to_redis(url, element, selector, confidence, strategy, context)
```

**Updated Get Method**:
```python
async def get_selector(
    self, url: str, element: str, dom_hash=None, context=None
) -> Optional[Dict[str, Any]]:
    """
    Get cached selector (dual-layer lookup).
    Week 4: Prefer stable entries, mark unstable hits.
    """
    # [Existing bypass logic]

    # Try Redis first
    redis_result = await self._get_from_redis(url, element, context)
    if redis_result:
        # Mark unstable hits for telemetry
        if not redis_result.get("stable", True):
            allow_fallback = os.getenv("PACTS_ALLOW_ID_FALLBACK", "true").lower() in ("1", "true")
            if not allow_fallback:
                logger.info(f"[CACHE][SKIP] Unstable cache entry: {element} (strategy: {redis_result.get('strategy')})")
                await self._record_metric("cache_miss")
                return None  # Skip unstable entries

            logger.warning(f"[CACHE][UNSTABLE-HIT] {element} → {redis_result['selector']} (strategy: {redis_result.get('strategy')})")
            await self._record_metric("cache_hit_unstable")

        await self._record_metric("cache_hit_redis")
        return redis_result

    # Try Postgres (similar logic)
    postgres_result = await self._get_from_postgres(url, element)
    if postgres_result:
        # [Same unstable-hit logic]
        await self._record_metric("cache_hit_postgres")
        return postgres_result

    # Cache miss
    await self._record_metric("cache_miss")
    return None
```

**Schema Update** (Postgres `selector_cache` table):
```sql
-- Migration: Add stability metadata
ALTER TABLE selector_cache ADD COLUMN stable BOOLEAN DEFAULT true;
ALTER TABLE selector_cache ADD COLUMN strategy VARCHAR(50);
```

**Lines to Modify**:
- `save_selector()` (~line 160)
- `get_selector()` (~line 85)
- Database schema migration (separate script)

---

### File 4: `backend/agents/oracle_healer.py`

**Changes**:
1. Prefer attribute-based rediscovery in healing
2. Tag heals with `unstable-heal: true` if ID path used
3. Use label-first mini-pipeline before other heuristics

**Updated Healing Logic**:
```python
async def heal_selector(state, intent):
    """
    Self-healing with label-first rediscovery.
    Week 4: Prioritize stable attributes over IDs.
    """
    element_text = intent.get("element")
    action = intent.get("action")

    # Try label-first mini-pipeline (stable strategies only)
    from backend.runtime.salesforce_helpers import build_attr_selector

    # Attempt attribute-based discovery
    discovered = await reprobe_with_alternates(state.browser.page, element_text, action)

    if discovered:
        new_selector = discovered["selector"]
        stable = discovered.get("stable", False)

        # Tag unstable heals for telemetry
        if not stable:
            logger.warning(f"[HEAL][UNSTABLE] Used ID-based heal: {new_selector}")
            heal_event["unstable_heal"] = True
        else:
            logger.info(f"[HEAL][STABLE] Used attribute-based heal: {new_selector}")
            heal_event["unstable_heal"] = False

        # Update state with new selector
        state.current_step_selector = new_selector
        return state
    else:
        # Discovery failed (existing guard logic)
        logger.warning(f"[HEAL] ⚠️ Discovery returned None for '{element_text}' (round {state.heal_round})")
        heal_event["actions"].append("discovery_none")
        state.current_step_selector = None
        return state
```

**Lines to Modify**: Healing discovery section (~lines 170-200)

---

### File 5: `backend/graph/build_graph.py`

**Changes**: None (env flags already passed via `os.getenv`)

**Verification**: Confirm `MAX_HEAL_ROUNDS` pattern applies to new flags.

---

### File 6: `docs/DAY-15-LIGHTNING-VALIDATION.md`

**Changes**: Append Week 4 Plan section

**Content**:
```markdown
## Week 4 - Label-First Discovery Implementation

**Goal**: Eliminate bypass toggle with stable, attribute-based selectors

**Plan**:
1. Discovery Priority: aria-label > name > placeholder > label[@for] > role+name > id
2. Cache Stores: input[aria-label="X"] instead of #input-390
3. Cache Policy: Block pure ID writes, prefer stable entries on reads
4. Rollout: Feature-flagged (PACTS_LABEL_FIRST=true)

**Acceptance Tests**:
- SF Lightning: 3x runs, 10/10 steps, 0 heals, cache hits present, stable:true
- Wikipedia: 2x runs, no regressions
- Warm-run durability: 3x form reopens, zero heals, selectors unchanged

**Timeline**: 1-2 days implementation + validation
```

**Lines to Add**: After Phase 2a section (~line 1012)

---

## 🚩 Feature Flags

### New Flags (Week 4)

| Flag | Default | Purpose | Rollout Phase |
|------|---------|---------|---------------|
| `PACTS_LABEL_FIRST` | `false` | Enable label-first discovery | Day 1: `true` |
| `PACTS_ALLOW_ID_CACHE` | `true` | Allow caching pure ID selectors | Day 1: `false` |
| `PACTS_ALLOW_ID_FALLBACK` | `true` | Allow reading old ID entries | Day 1: `false` (SF only) |

### Existing Flags (Keep)

| Flag | Current | Week 4 Status |
|------|---------|---------------|
| `PACTS_SF_BYPASS_FORM_CACHE` | `true` | Day 1: `true` (safety on), After green: `false` |
| `PACTS_SF_DRIFT_THRESHOLD` | `0.75` | Unchanged |
| `MAX_HEAL_ROUNDS` | `5` | Unchanged |

---

## ✅ Acceptance Tests

### A. Salesforce Lightning (Primary)

**Config**:
```bash
PACTS_LABEL_FIRST=true
PACTS_ALLOW_ID_CACHE=false
PACTS_ALLOW_ID_FALLBACK=false
PACTS_SF_BYPASS_FORM_CACHE=false  # After Day 1 green
```

**Run**: 3x headless `salesforce_opportunity_postlogin`

**Expected**:
- ✅ 10/10 steps (all PASS)
- ✅ 0 heals
- ✅ Cache hits present (warm runs)
- ✅ Selectors tagged `stable:true`
- ✅ Strategy: `aria-label`, `name`, or `placeholder` (not `id`)
- ✅ No drift invalidations between runs

**Log Evidence**:
```
[CACHE] 🎯 HIT (redis): Opportunity Name → input[aria-label="Opportunity Name"]
[CACHE] Metadata: stable=true, strategy=aria-label
[GATE] unique=True visible=True enabled=True stable=True
```

---

### B. Wikipedia (Control - No Regression)

**Config**:
```bash
PACTS_LABEL_FIRST=true
PACTS_ALLOW_ID_CACHE=true  # Allow IDs for non-Lightning apps
```

**Run**: 2x headless `wikipedia_search`

**Expected**:
- ✅ Test completes successfully
- ✅ Attribute/role strategies find elements when available
- ✅ IDs still allowed as fallback (not blocked)

---

### C. Warm-Run Durability (Lightning)

**Scenario**: Reopen Lightning form 3 times in same session

**Steps**:
1. Run Test 1: Fresh discovery
2. Run Test 2: Cache hit (warm)
3. Run Test 3: Cache hit (warm)

**Expected**:
- ✅ Test 1: PASS 10/10, selectors discovered, `stable:true`
- ✅ Test 2: PASS 10/10, cache hits, 0 heals, selectors unchanged
- ✅ Test 3: PASS 10/10, cache hits, 0 heals, selectors unchanged

---

### D. Telemetry Sanity

**Metrics to Verify**:
```json
{
  "strategy_used": "aria-label",
  "stable": true,
  "cache_hit_source": "redis",
  "unstable_heal": false,
  "cache_hit_stable": 8,
  "cache_hit_unstable": 0
}
```

---

## 🧪 Test Checklist (Execute in Order)

### 1. Unit Tests (Fast)

- [ ] `test_selector_normalization()` - Attribute-first selector building
- [ ] `test_cache_write_veto()` - Pure ID blocked when `ALLOW_ID_CACHE=false`
- [ ] `test_healer_label_first()` - Healer uses attribute pipeline
- [ ] `test_stable_tagging()` - Selectors tagged `stable:true/false` correctly

**Command**: `pytest backend/tests/unit/test_discovery.py -v`

---

### 2. E2E Quick Pass (Headed, Visual)

- [ ] Launch headed browser: `--headed --slow-mo 400`
- [ ] Navigate to Lightning form
- [ ] Verify `aria-label` exists on inputs (inspect element)
- [ ] Verify combobox buttons have `aria-label` or `name`
- [ ] Screenshot for evidence

**Command**: `python -m backend.cli.main test --req salesforce_opportunity_postlogin --headed --slow-mo 400`

---

### 3. E2E Batch (Headless)

- [ ] **Salesforce**: 3 runs (capture steps/heals/durations)
  - [ ] Test 1: PASS 10/10, 0 heals, fresh discovery
  - [ ] Test 2: PASS 10/10, 0 heals, cache hits
  - [ ] Test 3: PASS 10/10, 0 heals, cache hits
- [ ] **Wikipedia**: 2 runs (verify no regressions)

**Commands**:
```bash
for i in 1 2 3; do
  docker-compose run --rm pacts-runner python -m backend.cli.main test --req salesforce_opportunity_postlogin 2>&1 | tee /tmp/sf_label_first_run$i.log
done

docker-compose run --rm pacts-runner python -m backend.cli.main test --req wikipedia_search
```

---

### 4. Toggle Removal Rehearsal

- [ ] Set `PACTS_SF_BYPASS_FORM_CACHE=false`
- [ ] Run 2x Salesforce tests
- [ ] Expected: PASS 10/10, 0 heals (no bypass needed)

**Command**:
```bash
# In .env and docker-compose.yml
PACTS_SF_BYPASS_FORM_CACHE=false

docker-compose run --rm pacts-runner python -m backend.cli.main test --req salesforce_opportunity_postlogin
```

---

## 🚀 Rollout Plan

### Day 1 (Implementation + Safety-On Testing)

**Config**:
```bash
PACTS_LABEL_FIRST=true           # Enable new strategy
PACTS_ALLOW_ID_CACHE=false       # Block ID writes
PACTS_ALLOW_ID_FALLBACK=false    # Block ID reads (SF)
PACTS_SF_BYPASS_FORM_CACHE=true  # SAFETY ON (bypass still active)
```

**Actions**:
1. Implement all 4 files (discovery, helpers, cache, healer)
2. Run unit tests → all pass
3. Run E2E headed → verify aria-label/name present
4. Run Salesforce 2x → PASS 10/10 with bypass still ON (safety check)

**Expected**: No regressions, new code paths validated, bypass still protecting

---

### Day 2 (Bypass Removal)

**After Day 1 green**, update config:
```bash
PACTS_LABEL_FIRST=true           # Keep ON
PACTS_ALLOW_ID_CACHE=false       # Keep OFF
PACTS_ALLOW_ID_FALLBACK=false    # Keep OFF
PACTS_SF_BYPASS_FORM_CACHE=false # SAFETY OFF (bypass disabled)
```

**Actions**:
1. Run Salesforce 3x → PASS 10/10, 0 heals (warm runs use cached stable selectors)
2. Verify logs: `stable:true`, `strategy=aria-label/name`, cache hits present
3. Run Wikipedia 2x → PASS (no regressions)

**Expected**: 100% PASS without bypass, cache working on warm runs

---

### Day 3 (Validation + Documentation)

**Actions**:
1. Collect metrics: cache hit rate, strategy distribution, heal counts
2. Capture log evidence (screenshots/snippets)
3. Update `DAY-15-LIGHTNING-VALIDATION.md` with Week 4 results
4. Create PR with summary + evidence

**Deliverables**:
- Code PR (4 files + schema migration)
- Documentation update
- Log evidence (stable selectors, warm-run cache hits)

---

## 🔙 Rollback Plan

### Emergency Rollback (Single Commit Revert)

**If tests fail on Day 2**:
```bash
# Option A: Re-enable bypass
PACTS_SF_BYPASS_FORM_CACHE=true  # Restore safety

# Option B: Disable label-first
PACTS_LABEL_FIRST=false          # Restore old behavior

# Option C: Full revert
git revert <week-4-commit-sha>
```

**Impact**: Returns to Week 3 Phase 2a behavior (100% PASS with bypass)

---

### Rollback Checklist

- [ ] Re-enable `PACTS_SF_BYPASS_FORM_CACHE=true`
- [ ] Run 2x Salesforce tests → verify PASS 10/10
- [ ] Optionally set `PACTS_LABEL_FIRST=false`
- [ ] Document rollback reason in session notes

---

## 📦 Deliverables

### Code PR

**Branch**: `feat/week-4-label-first-discovery`

**Files Changed**: 5
1. `backend/agents/pom_builder.py` - Discovery pipeline
2. `backend/runtime/salesforce_helpers.py` - Attribute helpers
3. `backend/storage/selector_cache.py` - Stability tagging + veto
4. `backend/agents/oracle_healer.py` - Label-first healing
5. `backend/migrations/add_selector_stability.sql` - Schema update

**PR Description Template**:
```markdown
## Week 4 - Label-First Discovery Strategy

### Summary
Eliminates bypass toggle by prioritizing stable attributes over volatile IDs.

**Discovery Priority**: aria-label > name > placeholder > label[@for] > role+name > id

**Cache Stores**: `input[aria-label="X"]` instead of `#input-390`

**Result**: Warm runs PASS without bypass (cache durable across navigations)

### Changes
• pom_builder.py: Label-first discovery pipeline
• salesforce_helpers.py: Attribute selector builders
• selector_cache.py: Stability tagging + ID write veto
• oracle_healer.py: Stable-first healing
• Schema: Add `stable` + `strategy` columns

### Validation (3x SF tests, bypass OFF)
- Test 1: ✅ PASS 10/10, 0 heals, stable:true
- Test 2: ✅ PASS 10/10, 0 heals, cache hits
- Test 3: ✅ PASS 10/10, 0 heals, cache hits

### Metrics
- Strategy distribution: aria-label (60%), name (30%), role+name (10%)
- Cache hit rate: 95% (warm runs)
- Heal rate: 0% (no stale selectors)

### Rollback
Set `PACTS_SF_BYPASS_FORM_CACHE=true` or `PACTS_LABEL_FIRST=false`
```

---

### Documentation

**Files to Update**:
1. `docs/DAY-15-LIGHTNING-VALIDATION.md` - Add Week 4 results section
2. `docs/SELECTOR-POLICY.md` - NEW: Stable vs Unstable selector guide
3. `docs/INDEX.md` - Update with Week 4 files

---

### Log Evidence

**Required Screenshots/Snippets**:
1. **Stable selectors logged**:
   ```
   [CACHE] 🎯 HIT (redis): Opportunity Name → input[aria-label="Opportunity Name"]
   [CACHE] Metadata: stable=true, strategy=aria-label
   ```

2. **Warm-run cache hits**:
   ```
   Test 1: PASS 10/10, 0 heals (fresh discovery)
   Test 2: PASS 10/10, 0 heals (cache HIT, stable selectors)
   Test 3: PASS 10/10, 0 heals (cache HIT, stable selectors)
   ```

3. **Strategy distribution**:
   ```
   aria-label: 6 elements
   name: 3 elements
   role+name: 1 element
   id: 0 elements (blocked by ALLOW_ID_CACHE=false)
   ```

---

## 📝 Notes for Implementation

### Keep It Surgical

- ✅ Don't delete bypass toggle (safety valve)
- ✅ Don't refactor beyond strategy order + normalization
- ✅ Keep diffs small (< 300 lines total)
- ✅ Guard new behavior with feature flags

### Element Priority Logic

**If element has**:
1. `aria-label` → Use `tag[aria-label="X"]` (stable)
2. `name` attribute → Use `tag[name="X"]` (stable)
3. `placeholder` → Use `input[placeholder*="X"i]` (stable)
4. Associated `<label for="id">` → Use `#id` (unstable, but functional)
5. `role` + accessible name → Use `role=X[name*="Y"i]` (stable)
6. Only `id` → Use `#id` but DON'T cache (unstable)

### Fallback Safety

**If no stable attributes exist**:
- Discovery still returns `#id` selector
- Execution succeeds (element found)
- Cache write blocked (veto by `ALLOW_ID_CACHE=false`)
- Next run: Fresh discovery again (slower but safe)

**Trade-off**: Slightly slower for elements without attributes, but prevents stale cache hits.

---

## 🎯 Success Criteria

| Criterion | Target | Week 3 Phase 2a | Week 4 Goal |
|-----------|--------|-----------------|-------------|
| **Salesforce PASS rate** | 100% | 100% (with bypass) | 100% (no bypass) |
| **Heal rounds** | 0 | 0 | 0 |
| **Cache hit rate (warm)** | ≥80% | 0% (bypass skips cache) | ≥95% (stable selectors) |
| **Strategy: stable** | ≥90% | N/A | ≥90% (aria/name/placeholder) |
| **Bypass needed** | No | Yes | **No** ✅ |

---

## 📅 Timeline

| Day | Activity | Deliverable |
|-----|----------|-------------|
| **Day 1** | Implementation + Unit Tests | Code complete, tests green |
| **Day 2** | E2E Testing + Bypass Removal | 3x SF PASS, bypass OFF |
| **Day 3** | Documentation + PR | PR submitted, logs captured |

**Total**: 1-2 days (depends on test iterations)

---

## 🚀 Ready to Implement?

**Status**: 📋 **READY FOR EXECUTION**

**Pre-flight Checklist**:
- [x] Plan reviewed and approved
- [x] Acceptance tests defined
- [x] Rollback strategy documented
- [x] Feature flags specified
- [ ] Implementation started

**Start Command**: Begin with File 1 (`pom_builder.py`) discovery pipeline

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Next Review**: After Week 4 completion
