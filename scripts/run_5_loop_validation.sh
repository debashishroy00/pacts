#!/bin/bash
# PACTS v3.0 - Day 9: 5-Loop Cache Validation
# Target: ≥80% cache hit rate by loop 2

echo "======================================================================"
echo "PACTS v3.0 - 5-LOOP CACHE VALIDATION (Day 9)"
echo "======================================================================"
echo ""
echo "Target: ≥80% cache hit rate by loop 2"
echo "Expected: L1≈0%, L2≥80%, L3-L5≥90%"
echo ""

# Clear any existing cache to start fresh
echo "Clearing Redis to start fresh..."
docker-compose exec -T redis redis-cli FLUSHALL > /dev/null
echo "✅ Redis cleared"
echo ""

# Run 5 loops
for i in {1..5}; do
  echo "======================================================================"
  echo "LOOP $i/5 - Running wikipedia_search test"
  echo "======================================================================"

  # Run test
  docker-compose run --rm pacts-runner \
    python -m backend.cli.main test --req wikipedia_search 2>&1 | \
    grep -E "\[CACHE\]|\[POMBuilder\]|Verdict:|Steps Executed:"

  echo ""
  echo "Loop $i Complete - Fetching cache stats..."

  # Get cache stats
  docker-compose run --rm pacts-runner python -c "
import asyncio
import sys
from backend.storage.init import get_storage, shutdown_storage

async def main():
    storage = await get_storage()
    stats = await storage.selector_cache.get_cache_stats()

    redis_hits = stats.get('redis_hits', 0)
    postgres_hits = stats.get('postgres_hits', 0)
    misses = stats.get('misses', 0)
    hit_rate = stats.get('hit_rate', 0.0)
    drift = stats.get('drift_detections', 0)

    print(f'Loop $i Stats:')
    print(f'  Redis Hits: {redis_hits}')
    print(f'  Postgres Hits: {postgres_hits}')
    print(f'  Misses: {misses}')
    print(f'  Hit Rate: {hit_rate:.1f}%')
    print(f'  Drift Events: {drift}')

    # Check targets
    if i == 2 and hit_rate >= 80.0:
        print(f'  ✅ TARGET MET: Hit rate {hit_rate:.1f}% ≥ 80%')
    elif i == 2:
        print(f'  ⚠️  WARNING: Hit rate {hit_rate:.1f}% < 80% target')

    if i >= 3 and drift > 0:
        print(f'  ⚠️  WARNING: Drift detected in loop {i}')

    await shutdown_storage()

asyncio.run(main())
" 2>&1 | grep -v "Error in sync shutdown"

  echo ""
done

echo "======================================================================"
echo "5-LOOP VALIDATION COMPLETE"
echo "======================================================================"
echo ""
echo "Next: Review hit rate progression and verify targets"
