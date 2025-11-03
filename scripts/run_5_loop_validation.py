"""
PACTS v3.0 - Day 9: 5-Loop Cache Validation
Target: ≥80% cache hit rate by loop 2
"""

import subprocess
import sys
import time


def run_command(cmd: str, desc: str):
    """Run shell command and return output."""
    print(f"\n{desc}...")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr, result.returncode


def main():
    print("=" * 70)
    print("PACTS v3.0 - 5-LOOP CACHE VALIDATION (Day 9)")
    print("=" * 70)
    print()
    print("Target: >=80% cache hit rate by loop 2")
    print("Expected: L1~0%, L2>=80%, L3-L5>=90%")
    print()

    # Clear Redis to start fresh
    print("Clearing Redis to start fresh...")
    stdout, stderr, code = run_command(
        "docker-compose exec -T redis redis-cli FLUSHALL",
        "Flushing Redis"
    )
    if code == 0:
        print("[OK] Redis cleared")
    else:
        print(f"[WARN]  Redis flush failed (may not be critical): {stderr}")
    print()

    # Track metrics
    loop_results = []

    # Run 5 loops
    for i in range(1, 6):
        print("=" * 70)
        print(f"LOOP {i}/5 - Running wikipedia_search test")
        print("=" * 70)
        print()

        # Run test
        test_cmd = "docker-compose run --rm pacts-runner python -m backend.cli.main test --req wikipedia_search"
        print(f"Executing: {test_cmd}")
        print()

        stdout, stderr, code = run_command(test_cmd, f"Running loop {i}")

        # Print relevant output
        for line in stdout.split("\n"):
            if any(keyword in line for keyword in ["[CACHE]", "[POMBuilder]", "Verdict:", "Steps Executed:"]):
                print(line)

        print()
        print(f"Loop {i} Complete - Fetching cache stats...")
        print()

        # Get cache stats
        stats_cmd = """docker-compose run --rm pacts-runner python -c "
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

    print(f'STATS:{redis_hits},{postgres_hits},{misses},{hit_rate:.1f},{drift}')

    await shutdown_storage()

asyncio.run(main())
" """

        stdout, stderr, code = run_command(stats_cmd, "Fetching stats")

        # Parse stats
        redis_hits, postgres_hits, misses, hit_rate, drift = 0, 0, 0, 0.0, 0
        for line in stdout.split("\n"):
            if line.startswith("STATS:"):
                parts = line.replace("STATS:", "").split(",")
                redis_hits = int(parts[0])
                postgres_hits = int(parts[1])
                misses = int(parts[2])
                hit_rate = float(parts[3])
                drift = int(parts[4])
                break

        # Store results
        loop_results.append({
            "loop": i,
            "redis_hits": redis_hits,
            "postgres_hits": postgres_hits,
            "misses": misses,
            "hit_rate": hit_rate,
            "drift": drift
        })

        # Display stats
        print(f"Loop {i} Stats:")
        print(f"  Redis Hits: {redis_hits}")
        print(f"  Postgres Hits: {postgres_hits}")
        print(f"  Misses: {misses}")
        print(f"  Hit Rate: {hit_rate:.1f}%")
        print(f"  Drift Events: {drift}")

        # Check targets
        if i == 2:
            if hit_rate >= 80.0:
                print(f"  [OK] TARGET MET: Hit rate {hit_rate:.1f}% ≥ 80%")
            else:
                print(f"  [WARN]  WARNING: Hit rate {hit_rate:.1f}% < 80% target")

        if i >= 3 and drift > 0:
            print(f"  [WARN]  WARNING: Drift detected in loop {i}")

        print()

    # Final summary
    print("=" * 70)
    print("5-LOOP VALIDATION COMPLETE")
    print("=" * 70)
    print()

    print("Summary Table:")
    print(f"{'Loop':<6} {'Redis':<8} {'Postgres':<10} {'Misses':<8} {'Hit Rate':<10} {'Drift':<8} {'Status':<15}")
    print("-" * 70)

    for result in loop_results:
        status = ""
        if result["loop"] == 2:
            status = "[OK] TARGET" if result["hit_rate"] >= 80.0 else "[FAIL] MISS TARGET"
        elif result["loop"] >= 3:
            status = "[OK] STABLE" if result["drift"] == 0 else "[WARN]  DRIFT"

        print(f"{result['loop']:<6} {result['redis_hits']:<8} {result['postgres_hits']:<10} "
              f"{result['misses']:<8} {result['hit_rate']:<10.1f}% {result['drift']:<8} {status:<15}")

    print()

    # Final assessment
    loop2 = next((r for r in loop_results if r["loop"] == 2), None)
    if loop2:
        if loop2["hit_rate"] >= 80.0:
            print("[OK] SUCCESS: Loop 2 hit rate target met (≥80%)")
        else:
            print(f"[FAIL] FAILURE: Loop 2 hit rate {loop2['hit_rate']:.1f}% < 80% target")

    drift_loops_3_5 = sum(r["drift"] for r in loop_results if r["loop"] >= 3)
    if drift_loops_3_5 == 0:
        print("[OK] SUCCESS: Zero drift events on loops 3-5")
    else:
        print(f"[WARN]  WARNING: {drift_loops_3_5} drift events detected on loops 3-5")

    print()
    print("Next: Review metrics and proceed to Day 10 (measure speedup & stability)")


if __name__ == "__main__":
    main()
