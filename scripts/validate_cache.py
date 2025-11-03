"""
PACTS Cache Validation Script - Day 8-9 Priority

Runs 5-loop test to validate cache performance:
- Target: ≥80% cache hit rate by loop 2
- Verify: 0 drift re-discoveries on loops 3-5
- Report: Detailed cache statistics per loop
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.graph.state import RunState
from backend.graph.build_graph import ainvoke_graph
from backend.storage.init import get_storage, shutdown_storage


async def run_single_loop(loop_num: int, req_id: str) -> dict:
    """Run single test loop and collect metrics."""
    print(f"\n{'='*70}")
    print(f"LOOP {loop_num}/5 - Running test...")
    print(f"{'='*70}\n")

    # Build minimal state for wikipedia_search
    state = RunState(
        req_id=req_id,
        context={
            "url": "https://www.wikipedia.org",
            "browser_config": {
                "headless": True,
                "slow_mo": 0
            },
            # Simple test: search for "Python programming"
            "suite": {
                "req_id": req_id,
                "testcases": [{
                    "tc_id": "TC-001",
                    "title": "Wikipedia Search Test",
                    "steps": [
                        {
                            "action": "navigate",
                            "url": "https://www.wikipedia.org"
                        },
                        {
                            "action": "fill",
                            "element": "search_input",
                            "value": "Python programming"
                        },
                        {
                            "action": "click",
                            "element": "search_button"
                        }
                    ]
                }]
            }
        }
    )

    # Run pipeline
    result = await ainvoke_graph(state)

    return {
        "loop": loop_num,
        "verdict": result.verdict,
        "steps": result.step_idx,
        "heal_rounds": result.heal_round,
        "heal_events": len(result.heal_events)
    }


async def get_cache_metrics(storage) -> dict:
    """Get current cache statistics."""
    if not storage or not hasattr(storage, 'selector_cache'):
        return {
            "redis_hits": 0,
            "postgres_hits": 0,
            "misses": 0,
            "hit_rate": 0.0,
            "drift_detections": 0,
            "total_hits": 0
        }

    stats = await storage.selector_cache.get_cache_stats()
    total_hits = stats.get("redis_hits", 0) + stats.get("postgres_hits", 0)

    return {
        "redis_hits": stats.get("redis_hits", 0),
        "postgres_hits": stats.get("postgres_hits", 0),
        "misses": stats.get("misses", 0),
        "hit_rate": stats.get("hit_rate", 0.0),
        "drift_detections": stats.get("drift_detections", 0),
        "total_hits": total_hits
    }


async def main():
    """Run 5-loop cache validation test."""
    print("="*70)
    print("PACTS CACHE VALIDATION - Day 8-9 Priority")
    print("="*70)
    print("\nTargets:")
    print("  - ≥80% cache hit rate by loop 2")
    print("  - 0 drift re-discoveries on loops 3-5")
    print("  - Confirm SelectorCache.get_cache_stats() metrics")
    print()

    storage = None
    results = []
    metrics_per_loop = []

    try:
        # Initialize storage
        print("Initializing memory & persistence...")
        storage = await get_storage()

        if not storage:
            print("❌ Storage initialization failed")
            sys.exit(1)

        health = await storage.healthcheck()
        if not health.get("healthy"):
            print("❌ Storage health check failed")
            sys.exit(1)

        print("✅ Memory system ready\n")

        # Get baseline metrics
        baseline = await get_cache_metrics(storage)
        print(f"Baseline Cache State:")
        print(f"  Redis Hits: {baseline['redis_hits']}")
        print(f"  Postgres Hits: {baseline['postgres_hits']}")
        print(f"  Misses: {baseline['misses']}")
        print(f"  Hit Rate: {baseline['hit_rate']:.1f}%")

        # Run 5 loops
        for loop in range(1, 6):
            # Run test
            result = await run_single_loop(loop, "wikipedia_search")
            results.append(result)

            # Get metrics after this loop
            metrics = await get_cache_metrics(storage)

            # Calculate delta from previous loop
            if loop == 1:
                delta_hits = metrics['total_hits'] - baseline['total_hits']
                delta_misses = metrics['misses'] - baseline['misses']
            else:
                prev = metrics_per_loop[-1]
                delta_hits = metrics['total_hits'] - prev['total_hits']
                delta_misses = metrics['misses'] - prev['misses']

            metrics['delta_hits'] = delta_hits
            metrics['delta_misses'] = delta_misses
            metrics_per_loop.append(metrics)

            # Print loop summary
            print(f"\nLoop {loop} Summary:")
            print(f"  Verdict: {result['verdict']}")
            print(f"  Steps: {result['steps']}")
            print(f"  Heal Rounds: {result['heal_rounds']}")
            print(f"  Cache Δ: +{delta_hits} hits, +{delta_misses} misses")
            print(f"  Current Hit Rate: {metrics['hit_rate']:.1f}%")

            # Check targets
            if loop == 2 and metrics['hit_rate'] < 80.0:
                print(f"  ⚠️  WARNING: Hit rate {metrics['hit_rate']:.1f}% < 80% target")
            elif loop == 2 and metrics['hit_rate'] >= 80.0:
                print(f"  ✅ HIT RATE TARGET MET: {metrics['hit_rate']:.1f}% ≥ 80%")

            if loop >= 3 and metrics['drift_detections'] > metrics_per_loop[1].get('drift_detections', 0):
                print(f"  ⚠️  WARNING: Drift detected in loop {loop}")

        # Final report
        print("\n" + "="*70)
        print("CACHE VALIDATION RESULTS")
        print("="*70)
        print()

        print("Loop-by-Loop Metrics:")
        print(f"{'Loop':<6} {'Hits':<8} {'Misses':<8} {'Hit Rate':<10} {'Drift':<8} {'Status':<15}")
        print("-" * 70)

        for i, metrics in enumerate(metrics_per_loop, 1):
            status = "✅ PASS" if i >= 2 and metrics['hit_rate'] >= 80.0 else "⏳ Building"
            print(f"{i:<6} {metrics['total_hits']:<8} {metrics['misses']:<8} "
                  f"{metrics['hit_rate']:<10.1f}% {metrics['drift_detections']:<8} {status:<15}")

        print()

        # Final assessment
        final_metrics = metrics_per_loop[-1]
        loop2_metrics = metrics_per_loop[1] if len(metrics_per_loop) > 1 else None

        print("Final Assessment:")
        if loop2_metrics and loop2_metrics['hit_rate'] >= 80.0:
            print("  ✅ Cache hit rate target MET (≥80% by loop 2)")
        else:
            print(f"  ❌ Cache hit rate target MISSED ({loop2_metrics['hit_rate']:.1f}% < 80%)")

        # Check drift stability
        drift_loop3_5 = final_metrics['drift_detections'] - (loop2_metrics['drift_detections'] if loop2_metrics else 0)
        if drift_loop3_5 == 0:
            print("  ✅ Zero drift re-discoveries on loops 3-5")
        else:
            print(f"  ⚠️  {drift_loop3_5} drift detections on loops 3-5")

        print(f"\n  Overall Hit Rate: {final_metrics['hit_rate']:.1f}%")
        print(f"  Total Cache Hits: {final_metrics['total_hits']}")
        print(f"  Total Misses: {final_metrics['misses']}")
        print(f"  Total Drift Events: {final_metrics['drift_detections']}")

    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        if storage:
            await shutdown_storage()

    print("\n" + "="*70)
    print("CACHE VALIDATION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
