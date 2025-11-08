"""
Cached discovery wrapper - integrates SelectorCache with discovery.

Dual-layer caching:
    Read: Redis (1h TTL) → Postgres (7d retention) → Full Discovery
    Write: Postgres → Redis (warm cache)

Debug Mode:
    Set CACHE_DEBUG=true to see cache tier hits in console
"""

import os
import logging
import hashlib
from typing import Dict, Any, Optional

from .discovery import discover_selector
from ..storage.init import get_storage

logger = logging.getLogger(__name__)

# Debug flag
CACHE_DEBUG = os.getenv("CACHE_DEBUG", "false").lower() == "true"


async def discover_selector_cached(browser, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Discover selector with caching.

    Args:
        browser: Browser instance
        intent: {
            "element": str,
            "action": str,
            "value": Optional[str],
            "within": Optional[str]
        }

    Returns:
        {
            "selector": str,
            "score": float,
            "meta": {
                "strategy": str,
                "source": "redis" | "postgres" | "discovery",
                ...
            }
        }
        or None if discovery failed
    """
    # Check if memory is enabled
    storage = await get_storage()
    if not storage or not storage.selector_cache:
        # Memory disabled - fall back to direct discovery
        return await discover_selector(browser, intent)

    # Extract cache key components
    url = browser.page.url if browser and browser.page else ""
    element = intent.get("element", "")

    if not url or not element:
        # Invalid cache key - fall back to discovery
        return await discover_selector(browser, intent)

    # Calculate DOM hash for drift detection
    dom_hash = await _get_dom_hash(browser)

    # Try cache lookup
    try:
        cached = await storage.selector_cache.get_selector(url, element, dom_hash)

        if cached:
            # Cache hit!
            source = cached.get("source", "unknown")
            stable = cached.get("stable", False)  # Week 4: Track selector stability

            if CACHE_DEBUG:
                stable_indicator = "✓stable" if stable else "⚠volatile"
                print(
                    f"[CACHE] 🎯 HIT ({source}): {element} → {cached['selector'][:50]} ({stable_indicator})"
                )

            # Return in discover_selector format
            return {
                "selector": cached["selector"],
                "score": cached.get("confidence", 0.9),
                "meta": {
                    "strategy": cached.get("strategy", "cached"),
                    "source": source,
                    "cached": True,
                    "stable": stable,  # Week 4: Pass stability info
                },
            }

    except Exception as e:
        logger.warning(f"[CACHE] Error during lookup, falling back to discovery: {e}")

    # Cache miss - run full discovery
    if CACHE_DEBUG:
        print(f"[CACHE] ❌ MISS: {element} → running full discovery")

    result = await discover_selector(browser, intent)

    # Week 8 Phase B: Check if cache writes are disabled
    cache_writes_disabled = os.getenv("PACTS_CACHE_WRITES_DISABLED", "false").lower() == "true"

    if result and not cache_writes_disabled:
        # Cache successful discovery
        try:
            meta = result.get("meta", {})
            stable = meta.get("stable", False)  # Week 4: Extract stability flag

            await storage.selector_cache.save_selector(
                url=url,
                element=element,
                selector=result["selector"],
                confidence=result.get("score", 0.0),
                strategy=meta.get("strategy", "unknown"),
                dom_hash=dom_hash,
                stable=stable,  # Week 4: Pass stability to cache
            )

            if CACHE_DEBUG:
                stable_indicator = "✓stable" if stable else "⚠volatile"
                print(
                    f"[CACHE] 💾 SAVED: {element} → {result['selector'][:50]} (strategy: {meta.get('strategy')}, {stable_indicator})"
                )

            # Mark as newly discovered
            if "meta" not in result:
                result["meta"] = {}
            result["meta"]["source"] = "discovery"
            result["meta"]["cached"] = False

        except Exception as e:
            logger.warning(f"[CACHE] Error during save: {e}")

    return result


async def _get_dom_hash(browser) -> Optional[str]:
    """
    Calculate DOM hash for drift detection.

    Uses simple hash of body innerHTML to detect structural changes.

    Args:
        browser: Browser instance

    Returns:
        SHA256 hash of DOM structure or None
    """
    try:
        if not browser or not browser.page:
            return None

        # Get simplified DOM structure (tag names only, no text content)
        dom_structure = await browser.page.evaluate(
            """
            () => {
                function getStructure(el) {
                    if (!el || !el.tagName) return '';
                    const tag = el.tagName.toLowerCase();
                    const children = Array.from(el.children).map(getStructure).join('');
                    return tag + children;
                }
                return getStructure(document.body);
            }
            """
        )

        if not dom_structure:
            return None

        # Hash the structure
        return hashlib.sha256(dom_structure.encode()).hexdigest()

    except Exception as e:
        logger.warning(f"[CACHE] Error calculating DOM hash: {e}")
        return None


async def invalidate_selector_cache(browser, element: str):
    """
    Manually invalidate cached selector.

    Used when healing discovers selector is stale.

    Args:
        browser: Browser instance
        element: Element name to invalidate
    """
    storage = await get_storage()
    if not storage or not storage.selector_cache:
        return

    try:
        url = browser.page.url if browser and browser.page else ""
        if url and element:
            await storage.selector_cache.invalidate_selector(url, element)
            if CACHE_DEBUG:
                print(f"[CACHE] 🗑️ INVALIDATED: {element}")
    except Exception as e:
        logger.warning(f"[CACHE] Error during invalidation: {e}")


async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        {
            "redis_hits": int,
            "postgres_hits": int,
            "misses": int,
            "hit_rate": float,
            "drift_detections": int,
            "invalidations": int,
            "total_cached": int
        }
        or {} if cache disabled
    """
    storage = await get_storage()
    if not storage or not storage.selector_cache:
        return {}

    try:
        return await storage.selector_cache.get_cache_stats()
    except Exception as e:
        logger.warning(f"[CACHE] Error getting stats: {e}")
        return {}
