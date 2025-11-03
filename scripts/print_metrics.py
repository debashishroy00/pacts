"""
Print Metrics - Simple CLI to view PACTS metrics (Day 12 Part B)

Usage:
    python scripts/print_metrics.py
    python scripts/print_metrics.py --cache
    python scripts/print_metrics.py --heal
    python scripts/print_metrics.py --runs
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.init import get_storage


async def print_cache_metrics():
    """Print cache metrics."""
    storage = await get_storage()
    if not storage or not storage.selector_cache:
        print("❌ Storage not initialized")
        return

    stats = await storage.selector_cache.get_cache_stats()
    print("\n📊 CACHE METRICS")
    print("=" * 50)
    print(f"Redis Hits:      {stats['redis_hits']}")
    print(f"Postgres Hits:   {stats['postgres_hits']}")
    print(f"Misses:          {stats['misses']}")
    print(f"Hit Rate:        {stats['hit_rate']:.1f}%")
    print(f"Total Cached:    {stats['total_cached']}")
    print()


async def print_heal_metrics():
    """Print healing strategy metrics."""
    storage = await get_storage()
    if not storage or not storage.heal_history:
        print("❌ Storage not initialized")
        return

    strategies = await storage.heal_history.get_all_strategies()
    print("\n🩹 HEALING METRICS")
    print("=" * 70)
    print(f"{'Strategy':<20} {'Success':<10} {'Failure':<10} {'Rate':<10} {'Uses':<10}")
    print("-" * 70)

    for strat in strategies:
        print(
            f"{strat['strategy']:<20} "
            f"{strat['total_success']:<10} "
            f"{strat['total_failure']:<10} "
            f"{strat['success_rate']:.1f}%{'':<6} "
            f"{strat['usage_count']:<10}"
        )

    print()


async def print_run_metrics():
    """Print run statistics."""
    storage = await get_storage()
    if not storage or not storage.runs:
        print("❌ Storage not initialized")
        return

    stats = await storage.runs.get_run_stats()
    print("\n🏃 RUN METRICS")
    print("=" * 50)
    print(f"Total Runs:      {stats['total_runs']}")
    print(f"Passed:          {stats['passed']}")
    print(f"Failed:          {stats['failed']}")
    print(f"Success Rate:    {stats['success_rate']:.1f}%")
    print(f"Avg Heal Rounds: {stats['avg_heal_rounds']:.2f}")
    print(f"Avg Duration:    {stats['avg_duration_ms']:.0f}ms")
    print()


async def print_all_metrics():
    """Print all metrics."""
    await print_cache_metrics()
    await print_heal_metrics()
    await print_run_metrics()


async def main():
    parser = argparse.ArgumentParser(description="Print PACTS metrics")
    parser.add_argument("--cache", action="store_true", help="Show cache metrics only")
    parser.add_argument("--heal", action="store_true", help="Show healing metrics only")
    parser.add_argument("--runs", action="store_true", help="Show run metrics only")

    args = parser.parse_args()

    # If no specific flag, show all
    if not any([args.cache, args.heal, args.runs]):
        await print_all_metrics()
    else:
        if args.cache:
            await print_cache_metrics()
        if args.heal:
            await print_heal_metrics()
        if args.runs:
            await print_run_metrics()

    # Clean shutdown
    from backend.storage.init import shutdown_storage
    await shutdown_storage()


if __name__ == "__main__":
    asyncio.run(main())
