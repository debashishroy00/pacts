# PACTS v3.0 - Day 9-12 Action Plan

**Status**: Day 9 In Progress - 5-Loop Cache Validation Running
**Timeline**: 2025-11-03 to 2025-11-06
**Owner**: Week 2 Cache & Telemetry Sprint

---

## Day 9: 5-Loop Cache Validation (IN PROGRESS)

### Objective
Validate >=80% cache hit rate by loop 2, zero drift on loops 3-5

### Test Execution
```bash
# Running now (background process 078cd7)
python scripts/run_5_loop_validation.py
```

### Expected KPIs
- **Loop 1**: ~0% hit rate (building cache, discovery latency ~500-2000ms)
- **Loop 2**: **>=80% hit rate** [TARGET] (cache latency ~1-5ms)
- **Loops 3-5**: >=90% hit rate + **0 drift events** [TARGET]

### Success Criteria
1. [PENDING] Loop 2 hit rate >=80%
2. [PENDING] Loops 3-5 drift events = 0
3. [PENDING] Redis hits dominant (fast path working)
4. [PENDING] Postgres fallback working when Redis cleared
5. [PENDING] Hit rate calculation accurate

### Troubleshooting Scenarios

**If hit rate <80% on Loop 2**:
- Check DOM hash stability (Wikipedia banners/A-B tests)
- Verify ENABLE_MEMORY=true
- Check Redis TTL not expiring (should be 1h+)
- Confirm URL normalization (same origin/path)
- Review [CACHE] log lines for MISS reasons

**If drift detected on loops 3-5**:
- Check drift_threshold (default: 35%)
- Review DOM changes (dynamic content, timestamps)
- Verify selector stability across page loads
- Check for JavaScript-rendered elements

### Metrics to Capture
```python
# After test completion
{
    "loop_1": {"redis_hits": 0, "postgres_hits": 0, "misses": N, "hit_rate": 0%},
    "loop_2": {"redis_hits": N, "postgres_hits": 0, "misses": M, "hit_rate": >=80%},
    "loop_3": {"redis_hits": N+, "postgres_hits": 0, "misses": 0, "hit_rate": ~100%},
    "loop_4": {"redis_hits": N++, "postgres_hits": 0, "misses": 0, "hit_rate": ~100%},
    "loop_5": {"redis_hits": N+++, "postgres_hits": 0, "misses": 0, "hit_rate": ~100%}
}
```

---

## Day 10: Measure Speedup & Stability

### Objective
Quantify cache performance gains and validate stability

### Tasks

#### 1. Measure Discovery Latency (Cache Hit vs Miss)
```bash
# With cache (Redis hit)
docker-compose run --rm pacts-runner \
  python -m backend.cli.main test --req wikipedia_search

# With Postgres fallback only (clear Redis first)
docker-compose exec redis redis-cli FLUSHALL
docker-compose run --rm pacts-runner \
  python -m backend.cli.main test --req wikipedia_search

# With full discovery (clear both)
docker-compose exec redis redis-cli FLUSHALL
# Manually truncate selector_cache table in Postgres
docker-compose run --rm pacts-runner \
  python -m backend.cli.main test --req wikipedia_search
```

#### 2. Capture Latency Metrics
- **Redis Hit**: ~1-5ms (fast path)
- **Postgres Hit**: ~10-50ms (fallback)
- **Full Discovery**: ~500-2000ms (selector search + scoring)
- **Expected Speedup**: 100-400x

#### 3. Stability Check
- Run 10 consecutive tests
- Target: 0 drift events
- Target: 95%+ hit rate across all runs
- Target: No cache invalidations

### Success Criteria
- [ ] Median latency with cache <10ms
- [ ] Median latency without cache >500ms
- [ ] Speedup factor >=100x
- [ ] Zero drift events across 10 runs
- [ ] Hit rate stable at 95%+

---

## Day 11: Integrate HealHistory into OracleHealer

### Objective
Use historical healing data to prioritize strategies

### Architecture

**HealHistory Table** (existing):
```sql
CREATE TABLE heal_history (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    element TEXT NOT NULL,
    original_selector TEXT NOT NULL,
    successful_selector TEXT NOT NULL,
    strategy TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    outcome TEXT CHECK (outcome IN ('success', 'fail')) NOT NULL,
    heal_time_ms INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Integration Points**:
1. **OracleHealer reads top-N strategies**:
   ```python
   # In OracleHealer, before healing
   best_strategies = await heal_history.get_best_strategy(
       url=state.context["url"],
       element=failed_element,
       limit=3
   )
   # Try in order: placeholder, text_match, aria_label (most successful first)
   ```

2. **OracleHealer records outcomes**:
   ```python
   # After healing attempt
   await heal_history.record_outcome(
       url=url,
       element=element,
       original_selector=original,
       successful_selector=healed,
       strategy=strategy_name,
       confidence=score,
       outcome="success" if worked else "fail",
       heal_time_ms=latency
   )
   ```

### Implementation Steps

1. **Update OracleHealer**:
   - Add `heal_history` parameter to `__init__()`
   - Query `get_best_strategy()` before trying all strategies
   - Try learned strategies first, then fall back to full set
   - Record outcome after each heal attempt

2. **Add Metrics**:
   - `heal_strategy_cache_hit`: Used learned strategy
   - `heal_strategy_cache_miss`: Fell back to full search
   - `heal_time_improved`: Healing faster than median

3. **Test**:
   ```bash
   # Run test that requires healing
   docker-compose run --rm pacts-runner \
     python -m backend.cli.main test --req salesforce_opportunity_postlogin

   # Check heal_history for recorded outcomes
   docker-compose exec postgres psql -U pacts -d pacts \
     -c "SELECT element, strategy, outcome, heal_time_ms FROM heal_history ORDER BY created_at DESC LIMIT 10;"
   ```

### Success Criteria
- [ ] OracleHealer queries heal_history before healing
- [ ] Successful strategies recorded to heal_history
- [ ] Heal time reduced by 30%+ on repeated heals
- [ ] heal_strategy_cache_hit metric increments

---

## Day 12: Persist Runs (RunStorage) + Minimal Telemetry

### Objective
Store test execution data for analysis and reporting

### RunStorage Schema

```sql
CREATE TABLE runs (
    id SERIAL PRIMARY KEY,
    req_id TEXT NOT NULL,
    url TEXT NOT NULL,
    verdict TEXT CHECK (verdict IN ('pass', 'partial', 'fail')) NOT NULL,
    steps_executed INT NOT NULL,
    steps_total INT NOT NULL,
    heal_rounds INT NOT NULL DEFAULT 0,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_ms INT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE run_steps (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(id) ON DELETE CASCADE,
    step_idx INT NOT NULL,
    element TEXT NOT NULL,
    action TEXT NOT NULL,
    selector TEXT,
    strategy TEXT,
    outcome TEXT CHECK (outcome IN ('success', 'fail', 'skipped')) NOT NULL,
    latency_ms INT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE run_artifacts (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(id) ON DELETE CASCADE,
    artifact_type TEXT CHECK (artifact_type IN ('screenshot', 'test_file', 'video', 'log')) NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Integration Hooks

**Pipeline Integration**:
```python
# backend/graph/build_graph.py

async def ainvoke_graph(state: RunState):
    storage = await get_storage()

    # Create run record
    run_id = await storage.run_storage.create_run(
        req_id=state.req_id,
        url=state.context["url"],
        steps_total=len(state.context.get("suite", {}).get("testcases", [{}])[0].get("steps", []))
    )

    # Execute pipeline...
    result = await app.ainvoke(state, config={"recursion_limit": 100})

    # Save steps
    for step_data in result.get("step_history", []):
        await storage.run_storage.save_step(
            run_id=run_id,
            step_idx=step_data["idx"],
            element=step_data["element"],
            action=step_data["action"],
            selector=step_data.get("selector"),
            strategy=step_data.get("strategy"),
            outcome="success" if step_data.get("success") else "fail",
            latency_ms=step_data.get("latency_ms", 0)
        )

    # Save artifacts
    if "generated_file" in result.context:
        await storage.run_storage.save_artifact(
            run_id=run_id,
            artifact_type="test_file",
            file_path=result.context["generated_file"]
        )

    # Update run with final verdict
    await storage.run_storage.update_run(
        run_id=run_id,
        verdict=result.verdict,
        steps_executed=result.step_idx,
        heal_rounds=result.heal_round
    )

    return result
```

### Telemetry Queries

```python
# scripts/db_check.py

async def get_run_metrics():
    """Get basic run telemetry."""
    async with db.pool.acquire() as conn:
        # Success rate
        success_rate = await conn.fetchval("""
            SELECT
                ROUND(100.0 * COUNT(*) FILTER (WHERE verdict = 'pass') / COUNT(*), 1)
            FROM runs
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)

        # Total runs
        total_runs = await conn.fetchval("""
            SELECT COUNT(*) FROM runs
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)

        # Median duration
        median_duration = await conn.fetchval("""
            SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms)
            FROM runs
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)

        # Top failing elements
        top_failures = await conn.fetch("""
            SELECT
                element,
                COUNT(*) as failure_count
            FROM run_steps
            WHERE outcome = 'fail'
                AND created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY element
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """)

        return {
            "success_rate": success_rate,
            "total_runs": total_runs,
            "median_duration_ms": median_duration,
            "top_failures": top_failures
        }
```

### Smoke Test

```bash
# Run 2 tests
docker-compose run --rm pacts-runner \
  python -m backend.cli.main test --req wikipedia_search

docker-compose run --rm pacts-runner \
  python -m backend.cli.main test --req github_search

# Check runs table
docker-compose exec postgres psql -U pacts -d pacts \
  -c "SELECT req_id, verdict, steps_executed, duration_ms FROM runs ORDER BY created_at DESC LIMIT 5;"

# Get telemetry
docker-compose run --rm pacts-runner python scripts/db_check.py --metrics
```

### Success Criteria
- [ ] `create_run()` called at pipeline start
- [ ] `save_step()` called after each step
- [ ] `save_artifact()` called for screenshots/tests
- [ ] `update_run()` called with final verdict
- [ ] Telemetry queries return accurate metrics

---

## Week 2 Progress Tracker

### Completed ✅
- [x] Day 8: Cache infrastructure validated (Redis + Postgres dual-layer)
- [x] Day 8: Anthropic SDK fixed (httpx compatibility)
- [x] Day 8: End-to-end pipeline working (wikipedia_search PASS)

### In Progress 🔄
- [ ] Day 9: 5-loop cache validation (RUNNING NOW)

### Pending ⏳
- [ ] Day 10: Measure speedup & stability
- [ ] Day 11: Integrate HealHistory
- [ ] Day 12: RunStorage + telemetry

### Week 2 Target (Day 13-14)
- [ ] Salesforce regression (full 15-step test)
- [ ] Stability hardening (Docker, Redis, Postgres tuning)

---

## Commands Reference

### Day 9: Cache Validation
```bash
# 5-loop test
python scripts/run_5_loop_validation.py

# Manual loop
for i in {1..5}; do
  docker-compose run --rm pacts-runner \
    python -m backend.cli.main test --req wikipedia_search
done

# Check cache stats
docker-compose run --rm pacts-runner python -c "
import asyncio
from backend.storage.init import get_storage

async def stats():
    storage = await get_storage()
    stats = await storage.selector_cache.get_cache_stats()
    print(stats)

asyncio.run(stats())
"
```

### Day 10: Speedup Measurement
```bash
# Clear Redis (force Postgres fallback)
docker-compose exec redis redis-cli FLUSHALL

# Clear Postgres cache (force full discovery)
docker-compose exec postgres psql -U pacts -d pacts \
  -c "TRUNCATE selector_cache;"

# Time each scenario
time docker-compose run --rm pacts-runner \
  python -m backend.cli.main test --req wikipedia_search
```

### Day 11: HealHistory Queries
```bash
# Check heal_history
docker-compose exec postgres psql -U pacts -d pacts \
  -c "SELECT element, strategy, outcome, heal_time_ms FROM heal_history ORDER BY created_at DESC LIMIT 10;"

# Get best strategies
docker-compose exec postgres psql -U pacts -d pacts \
  -c "SELECT strategy, COUNT(*) as success_count FROM heal_history WHERE outcome='success' GROUP BY strategy ORDER BY COUNT(*) DESC;"
```

### Day 12: RunStorage Queries
```bash
# Recent runs
docker-compose exec postgres psql -U pacts -d pacts \
  -c "SELECT req_id, verdict, steps_executed, duration_ms FROM runs ORDER BY created_at DESC LIMIT 10;"

# Success rate (24h)
docker-compose exec postgres psql -U pacts -d pacts \
  -c "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE verdict='pass') / COUNT(*), 1) as success_rate FROM runs WHERE created_at >= NOW() - INTERVAL '24 hours';"

# Get telemetry
docker-compose run --rm pacts-runner python scripts/db_check.py --metrics
```

---

## Guardrails

### Version Control
- [ ] Poetry lock committed after dependency changes
- [ ] Rebuild runner after updating requirements.poetry.txt
- [ ] Git commit after each major milestone

### Performance
- [ ] Redis MAXMEMORY_POLICY = allkeys-lru
- [ ] Redis cache TTL >= 1 hour for hit testing
- [ ] Postgres retention: 7d for selector_cache
- [ ] Don't clean cache during active testing

### Compatibility
- [ ] Keep httpx <0.28.0 for anthropic 0.39.0 compatibility
- [ ] LangChain versions aligned (0.3.x)
- [ ] Docker Compose obsolete version warning (ignored for now)

---

## KPIs & Targets

### Cache Performance (Day 9-10)
- **Loop 2 Hit Rate**: >=80% [CRITICAL]
- **Loops 3-5 Drift**: 0 events [CRITICAL]
- **Redis Hits**: Dominant in loops 2-5
- **Discovery Latency**: 500-2000ms (baseline)
- **Cache Latency**: 1-5ms (Redis), 10-50ms (Postgres)
- **Speedup**: 100-400x

### Healing Performance (Day 11)
- **Heal Time Reduction**: >=30% on repeated heals
- **Strategy Cache Hit**: >=50% on second+ heals
- **Heal Success Rate**: >=85%

### Run Tracking (Day 12)
- **Runs Recorded**: 100%
- **Steps Captured**: 100%
- **Artifacts Saved**: 100% (screenshots + test files)
- **Query Performance**: <100ms for dashboard metrics

---

## Next Steps After Day 12

1. **Week 3: Advanced Telemetry**
   - LangSmith integration
   - OpenTelemetry tracing
   - Grafana dashboards

2. **Week 3: Production Hardening**
   - CI/CD pipeline with poetry export
   - Docker multi-stage builds
   - Health monitoring endpoints

3. **Week 3: Salesforce Regression**
   - Full 15-step Lightning test
   - "New" button disambiguation validation
   - Combobox deterministic behavior
   - Screenshot pipeline verification

---

**Status**: Day 9 in progress (5-loop test running)
**Next Milestone**: Day 9 completion + hit rate analysis
**Owner**: Week 2 Sprint (Cache & Telemetry)
**Target Completion**: 2025-11-06 EOD
