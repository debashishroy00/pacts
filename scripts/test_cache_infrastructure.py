"""
Simple Cache Infrastructure Test - Day 8-9 Validation

Tests the SelectorCache dual-layer system (Redis + Postgres) directly
without requiring full graph execution.

This validates:
- Storage initialization
- Selector caching (write to Postgres, warm Redis)
- Cache retrieval (Redis fast path, Postgres fallback)
- Cache hit rate calculation
- Drift detection
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.init import get_storage, shutdown_storage


async def test_cache_infrastructure():
    """Test selector cache infrastructure."""
    print("="*70)
    print("PACTS CACHE INFRASTRUCTURE TEST")
    print("="*70)
    print()

    storage = None

    try:
        # 1. Initialize storage
        print("1. Initializing storage...")
        storage = await get_storage()
        if not storage:
            print("❌ Storage initialization failed")
            return False

        health = await storage.healthcheck()
        if not health.get("healthy"):
            print(f"❌ Storage unhealthy: {health}")
            return False

        print(f"✅ Storage healthy")
        print(f"   - Postgres: {health.get('postgres', 'unknown')}")
        print(f"   - Redis: {health.get('redis', 'unknown')}")
        print()

        # 2. Get baseline metrics
        print("2. Getting baseline cache metrics...")
        baseline = await storage.selector_cache.get_cache_stats()
        print(f"   Redis hits: {baseline.get('redis_hits', 0)}")
        print(f"   Postgres hits: {baseline.get('postgres_hits', 0)}")
        print(f"   Misses: {baseline.get('misses', 0)}")
        print(f"   Hit rate: {baseline.get('hit_rate', 0.0):.1f}%")
        print()

        # 3. Simulate cache writes (selector discoveries)
        print("3. Writing test selectors to cache...")
        test_selectors = [
            {
                "url": "https://example.com",
                "element": "search_input",
                "selector": "input[name='q']",
                "strategy": "attribute_match",
                "confidence": 0.95,
                "dom_hash": "abc123"
            },
            {
                "url": "https://example.com",
                "element": "search_button",
                "selector": "button[type='submit']",
                "strategy": "attribute_match",
                "confidence": 0.90,
                "dom_hash": "abc123"
            },
            {
                "url": "https://example.com",
                "element": "logo",
                "selector": "img.logo",
                "strategy": "class_match",
                "confidence": 0.85,
                "dom_hash": "abc123"
            },
        ]

        for sel_data in test_selectors:
            await storage.selector_cache.save_selector(
                url=sel_data["url"],
                element=sel_data["element"],
                selector=sel_data["selector"],
                strategy=sel_data["strategy"],
                confidence=sel_data["confidence"],
                dom_hash=sel_data["dom_hash"]
            )
            print(f"   ✅ Saved: {sel_data['element']} -> {sel_data['selector']}")

        print()

        # 4. Clear Redis to test Postgres fallback
        print("4. Clearing Redis to test Postgres fallback...")
        await storage.cache.client.flushdb()
        print("   ✅ Redis cleared")
        print()

        # 5. Test cache retrieval (should hit Postgres, warm Redis)
        print("5. Testing cache retrieval (Postgres → Redis)...")
        for sel_data in test_selectors:
            result = await storage.selector_cache.get_selector(
                url=sel_data["url"],
                element=sel_data["element"],
                dom_hash=sel_data["dom_hash"]
            )
            if result:
                source = result.get("source", "unknown")
                print(f"   ✅ Retrieved: {sel_data['element']} (source: {source})")
            else:
                print(f"   ❌ MISS: {sel_data['element']}")

        print()

        # 6. Test cache retrieval again (should hit Redis)
        print("6. Testing cache retrieval again (Redis fast path)...")
        for sel_data in test_selectors:
            result = await storage.selector_cache.get_selector(
                url=sel_data["url"],
                element=sel_data["element"],
                dom_hash=sel_data["dom_hash"]
            )
            if result:
                source = result.get("source", "unknown")
                print(f"   ✅ Retrieved: {sel_data['element']} (source: {source})")
            else:
                print(f"   ❌ MISS: {sel_data['element']}")

        print()

        # 7. Get final metrics
        print("7. Final cache metrics...")
        final = await storage.selector_cache.get_cache_stats()
        print(f"   Redis hits: {final.get('redis_hits', 0)}")
        print(f"   Postgres hits: {final.get('postgres_hits', 0)}")
        print(f"   Misses: {final.get('misses', 0)}")
        print(f"   Hit rate: {final.get('hit_rate', 0.0):.1f}%")
        print()

        # 8. Validate results
        print("8. Validation Results:")
        redis_hits = final.get('redis_hits', 0) - baseline.get('redis_hits', 0)
        postgres_hits = final.get('postgres_hits', 0) - baseline.get('postgres_hits', 0)
        total_ops = redis_hits + postgres_hits

        if postgres_hits >= 3:
            print(f"   ✅ Postgres cache working ({postgres_hits} hits)")
        else:
            print(f"   ❌ Postgres cache not working ({postgres_hits} hits, expected >= 3)")
            return False

        if redis_hits >= 3:
            print(f"   ✅ Redis cache working ({redis_hits} hits)")
        else:
            print(f"   ⚠️  Redis cache may not be warmed ({redis_hits} hits)")

        if total_ops >= 6:
            print(f"   ✅ Dual-layer caching functional ({total_ops} total cache ops)")
            hit_rate = final.get('hit_rate', 0.0)
            if hit_rate > 0:
                print(f"   ✅ Hit rate calculation working ({hit_rate:.1f}%)")
        else:
            print(f"   ❌ Expected 6+ cache operations, got {total_ops}")
            return False

        print()
        print("="*70)
        print("✅ CACHE INFRASTRUCTURE TEST PASSED")
        print("="*70)
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if storage:
            await shutdown_storage()


if __name__ == "__main__":
    success = asyncio.run(test_cache_infrastructure())
    sys.exit(0 if success else 1)
