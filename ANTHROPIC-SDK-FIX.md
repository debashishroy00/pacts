# Anthropic SDK Compatibility Fix

**Date**: 2025-11-03
**Status**: ✅ RESOLVED
**Fix Method**: httpx version downgrade

---

## Problem

### Error Encountered
```
TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
  File "/usr/local/lib/python3.11/site-packages/anthropic/_base_client.py", line 754, in __init__
    super().__init__(**kwargs)
```

### Root Cause
- **anthropic SDK** `0.39.0` internally passes `proxies=` to httpx.Client()
- **httpx** `0.28.x` **removed** the `proxies` parameter
- **Incompatibility**: anthropic 0.39.0 not compatible with httpx >= 0.28.0

---

## Solution

### Fix Applied: Downgrade httpx

```bash
# Pin httpx to version compatible with anthropic 0.39.0
poetry add "httpx>=0.23.0,<0.28.0"

# Result: httpx downgraded from 0.28.1 → 0.27.2
```

### Updated Dependencies

**Before**:
```
anthropic==0.39.0
httpx==0.28.1  # ❌ Incompatible
```

**After**:
```
anthropic==0.39.0
httpx==0.27.2  # ✅ Compatible
```

---

## Verification

### Test 1: Client Initialization ✅

```python
import anthropic
client = anthropic.Anthropic(api_key=api_key)
# ✅ Client initialized: Anthropic
```

### Test 2: API Call ✅

```python
resp = client.messages.create(
    model='claude-3-5-haiku-20241022',
    max_tokens=50,
    temperature=0,
    messages=[{'role': 'user', 'content': 'Reply with just: PONG'}]
)
# ✅ API call successful
# Model: claude-3-5-haiku-20241022
# Response: PONG
```

### Test 3: End-to-End Pipeline ✅

```bash
docker-compose run --rm pacts-runner \
  python -m backend.cli.main test --req wikipedia_search
```

**Results**:
- ✅ Planner: LLM natural language parsing working
- ✅ POMBuilder: Selector discovery working
- ✅ Executor: Browser automation working
- ✅ Cache: MISS → SAVE working
- ✅ Verdict: **PASS**
- ✅ Artifact: `generated_tests/test_wikipedia_search.py`

---

## Cache Performance (Loop 1)

### Cache Operations

```
[CACHE] ❌ MISS: Search Wikipedia → running full discovery
[CACHE] 💾 SAVED: Search Wikipedia → #searchInput (strategy: placeholder)
```

### Metrics
- **Redis Hits**: 0 (first run)
- **Postgres Hits**: 0 (first run)
- **Misses**: 1 (expected - building cache)
- **Selectors Saved**: 1 (`Search Wikipedia` → `#searchInput`)

**Expected Next Run**:
- Cache HIT on `Search Wikipedia`
- Latency: ~1-5ms (Redis) vs ~500-2000ms (discovery)
- **Target Loop 2**: ≥80% cache hit rate

---

## Why httpx 0.27.2 Instead of Latest?

### Decision Rationale

1. **anthropic SDK 0.39.0** dependency constraint: `httpx >=0.23.0,<1`
2. **httpx 0.28.x** introduced breaking API change (removed `proxies=`)
3. **httpx 0.27.2** is the **latest stable** version before the breaking change
4. **Poetry resolution**: Automatically selected 0.27.2 when constrained to `<0.28.0`

### Alternative Solutions (Not Used)

**Option A**: Upgrade Anthropic SDK to 1.x
- ❌ Not available in Poetry repository (max version: 0.39.0)
- ⏳ Would require updating to anthropic 1.x when available

**Option B**: Custom httpx.Client injection
- ❌ More complex, requires code changes
- ❌ Maintenance burden across multiple files

**Option C (CHOSEN)**: Pin httpx < 0.28.0
- ✅ Zero code changes
- ✅ Works with existing anthropic 0.39.0
- ✅ Clean Poetry lockfile
- ✅ Proven stable (anthropic SDK designed for this version range)

---

## Future Upgrade Path

### When to Upgrade

Upgrade anthropic SDK when:
1. anthropic 1.x becomes available in Poetry
2. httpx compatibility confirmed with anthropic 1.x
3. No breaking changes in anthropic API

### Upgrade Steps

```bash
# 1. Check latest anthropic version
poetry show anthropic

# 2. If 1.x available, upgrade
poetry add "anthropic>=1.0,<2.0"

# 3. Remove httpx constraint (let it upgrade to 0.28+)
poetry add "httpx>=0.23.0,<1"

# 4. Test
docker-compose build pacts-runner
docker-compose run --rm pacts-runner python -c "
import anthropic
client = anthropic.Anthropic(api_key='test')
print('SDK OK')
"
```

---

## Updated pyproject.toml

```toml
[tool.poetry.dependencies]
python = "^3.11"

# Core runtime
anthropic = "^0.39"
playwright = "^1.47"
asyncpg = "^0.29"
psycopg = {extras = ["binary"], version = "^3.2.12"}
redis = {extras = ["hiredis"], version = "^7.0.1"}
pydantic = "^2.8"
pydantic-settings = "^2.4"
python-dotenv = "^1.0"
click = "^8.0"

# httpx version constrained for anthropic compatibility
httpx = ">=0.23.0,<0.28.0"  # ← FIX APPLIED

# LangGraph + LangChain family
langgraph = ">=0.2,<0.3"
langchain = ">=0.3,<0.4"
langchain-core = ">=0.3,<0.4"
langchain-community = ">=0.3,<0.4"
mcp = ">=1.0,<2.0"
jinja2 = ">=3.0,<4.0"
```

**Note**: The constraint is implicit via Poetry's resolution. httpx will stay at 0.27.2 until anthropic is upgraded.

---

## Build Metrics

### Container Build

```
Build Time: ~55 seconds
Total Layers: 8
Final Size: ~1.5 GB (with Playwright browser)
Dependencies: 80 packages
```

### Dependency Validation

```python
# Dockerfile.runner verification step
RUN python -c "import anthropic, playwright, asyncpg, redis; \
               print('✅ All dependencies loaded successfully')"
```

**Result**: ✅ All dependencies loaded successfully

---

## Impact on Week 2 Priorities

### Day 8-9: Cache Validation ✅

- ✅ Cache infrastructure validated
- ✅ Anthropic SDK fixed and tested
- ✅ Full end-to-end test working
- ⏳ **Next**: Run 5-loop cache validation test

### Day 9 Next Steps

1. **Run 5-Loop Cache Test**:
   ```bash
   # Loop 1: Build cache (0% hit rate)
   # Loop 2: Validate ≥80% cache hit rate
   # Loops 3-5: Confirm stability + 0 drift

   for i in {1..5}; do
     echo "=== LOOP $i ==="
     docker-compose run --rm pacts-runner \
       python -m backend.cli.main test --req wikipedia_search
   done
   ```

2. **Capture Metrics**: Use `get_cache_stats()` after each loop

3. **Validate Targets**:
   - ✅ Loop 2: ≥80% cache hit rate
   - ✅ Loops 3-5: 0 drift re-discoveries

---

## Lessons Learned

### What Worked

1. **Poetry dependency management**: SAT solver prevented version conflicts
2. **Explicit version constraints**: `<0.28.0` avoided breaking change
3. **Container verification**: Dockerfile validation step caught issues early
4. **Incremental testing**: Smoke tests before full pipeline saved time

### What to Improve

1. **Pin critical dependencies**: Lock httpx version explicitly in pyproject.toml
2. **Monitor SDK updates**: Check anthropic SDK releases monthly
3. **Test compatibility early**: Run SDK smoke tests before full integration

---

## Summary

**Problem**: Anthropic SDK 0.39.0 incompatible with httpx 0.28.x

**Solution**: Downgraded httpx from 0.28.1 → 0.27.2

**Status**: ✅ FULLY RESOLVED

**Verification**:
- ✅ Client initialization working
- ✅ API calls working (Claude 3.5 Haiku)
- ✅ End-to-end pipeline working (wikipedia_search PASS)
- ✅ Cache infrastructure functional

**Next**: Run 5-loop cache validation to hit Week 2 Day 8-9 targets

---

**Generated**: 2025-11-03 00:42 EST
**Fix Applied By**: httpx version constraint (`<0.28.0`)
**Verified By**: Full end-to-end test (wikipedia_search)
