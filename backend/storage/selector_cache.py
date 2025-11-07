"""
Selector Cache - Dual-layer caching for POM selectors.

Architecture:
    Read:  Redis (1h TTL) → Postgres (7d retention) → Discovery
    Write: Postgres → Redis (warm cache)

Drift Detection:
    - 2 consecutive misses → invalidate
    - DOM hash Δ > 35% → invalidate
"""

import os
import logging
import hashlib
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

from .base import BaseStorage

logger = logging.getLogger(__name__)

# Phase 2a: Optional Lightning form cache bypass (Week 3)
BYPASS_SF_CACHE = os.getenv("PACTS_SF_BYPASS_FORM_CACHE", "false").lower() in ("1", "true", "yes")


def _session_key(ctx: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate session-scoped cache key component.

    Week 3 Patch: Includes domain+path+user+session_epoch to prevent
    cross-session ID drift reuse (e.g., #input-339 from old session).

    Fallback to date hour bucket to avoid unbounded reuse.

    Args:
        ctx: Context dict with url, auth_user, session_epoch, etc.

    Returns:
        12-character hash for session scope
    """
    if not ctx:
        ctx = {}

    url = (ctx.get("url") or "").split("?")[0]
    domain = url.split("/")[2] if "://" in url else url
    path = "/" + "/".join(url.split("/")[3:]) if "://" in url else ""
    user = ctx.get("auth_user") or "unknown"
    sess_epoch = ctx.get("session_epoch") or ctx.get("session_start_epoch") or 0

    # If no session epoch, use hour bucket as fallback
    if not sess_epoch:
        sess_epoch = int(datetime.now().timestamp() // 3600)  # Hour bucket

    raw = json.dumps([domain, path, user, int(sess_epoch)], separators=(",", ":"))
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


class SelectorCache(BaseStorage):
    """
    Manages selector caching with Redis (fast) + Postgres (persistent).

    Telemetry Counters:
    - cache_hit_redis: Fast cache hits
    - cache_hit_postgres: Persistent cache hits
    - cache_miss: Full discovery required
    - cache_invalidated: Drift detected
    - drift_detected: DOM changes detected
    """

    def __init__(self, db, cache):
        super().__init__(db, cache)
        self._redis_ttl = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # 1 hour
        self._postgres_retention_days = int(
            os.getenv("SELECTOR_CACHE_RETENTION_DAYS", "7")
        )
        self._drift_threshold = float(os.getenv("CACHE_DRIFT_THRESHOLD", "35.0"))

    # ==========================================================================
    # Public API
    # ==========================================================================

    async def get_selector(
        self, url: str, element: str, dom_hash: Optional[str] = None, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached selector (dual-layer lookup).

        Read Pattern:
        1. Check Redis (fast, 1-hour TTL)
        2. Check Postgres (persistent, 7-day retention)
        3. Return None (cache miss, run discovery)

        Args:
            url: Page URL
            element: Element name
            dom_hash: Current DOM hash for drift detection (optional)

        Returns:
            {
                "selector": str,
                "strategy": str,
                "confidence": float,
                "source": "redis" | "postgres",
                "last_verified": timestamp,
                "stable": bool  # Week 4: Whether selector uses stable attributes
            }
            or None if cache miss
        """
        # Phase 2a: Optional Lightning form bypass
        if BYPASS_SF_CACHE:
            from backend.runtime.salesforce_helpers import is_lightning_form_url
            if is_lightning_form_url(url):
                logger.info(f"[CACHE][BYPASS] Lightning form detected; skipping cache for '{element}' @ {self._normalize_url(url)}")
                await self._record_metric("cache_miss")
                return None  # Force fresh discovery

        # Try Redis first (fast path)
        redis_result = await self._get_from_redis(url, element, context)
        if redis_result:
            # Validate with drift detection
            if dom_hash and await self._check_drift(url, element, dom_hash):
                logger.info(f"[CACHE] 🔄 Drift detected for {element}, invalidating")
                await self._record_metric("drift_detected")
                await self.invalidate_selector(url, element)
                return None

            await self._record_metric("cache_hit_redis")
            redis_result["source"] = "redis"
            return redis_result

        # Try Postgres (persistent cache)
        postgres_result = await self._get_from_postgres(url, element)
        if postgres_result:
            # Validate with drift detection
            if dom_hash and await self._check_drift(url, element, dom_hash):
                logger.info(f"[CACHE] 🔄 Drift detected for {element}, invalidating")
                await self._record_metric("drift_detected")
                await self.invalidate_selector(url, element)
                return None

            await self._record_metric("cache_hit_postgres")

            # Warm Redis cache
            await self._save_to_redis(
                url,
                element,
                postgres_result["selector"],
                postgres_result["confidence"],
                postgres_result["strategy"],
                context,
                stable=False,  # Week 4: Postgres doesn't track stability (no schema change)
            )

            postgres_result["source"] = "postgres"
            return postgres_result

        # Cache miss - full discovery needed
        await self._record_metric("cache_miss")
        await self._increment_miss_count(url, element)
        return None

    async def save_selector(
        self,
        url: str,
        element: str,
        selector: str,
        confidence: float,
        strategy: str,
        dom_hash: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stable: bool = False,  # Week 4: Track selector stability
    ):
        """
        Save selector to both caches.

        Week 8 EDR: STABLE-ONLY caching policy enforced.
        Volatile selectors (role+name, id, class) are rejected to prevent cache pollution.

        Write Pattern:
        1. Reject if stable=False (Week 8 EDR policy)
        2. Save to Postgres (persistent, source of truth)
        3. Save to Redis (fast cache)
        4. Store DOM hash for drift detection

        Args:
            url: Page URL
            element: Element name
            selector: CSS/XPath selector
            confidence: Confidence score (0.0-1.0)
            strategy: Discovery strategy used
            dom_hash: DOM hash for drift detection
            stable: Week 8 - Whether selector uses stable attributes (aria-label/name/placeholder/data-*)
        """
        # Week 8 EDR: Enforce stable-only caching policy
        if not stable:
            logger.warning(
                f"[CACHE] ⏩ SKIPPED (VOLATILE): {element} → {selector[:50]} "
                f"(strategy: {strategy}, stable={stable})"
            )
            await self._record_metric("volatile_selector_skipped")
            return  # Do not cache volatile selectors

        url_pattern = self._normalize_url(url)

        # Save to Postgres (upsert)
        await self.db.execute(
            """
            INSERT INTO selector_cache (
                url_pattern, element_name, selector, strategy, confidence,
                hit_count, miss_count, last_verified_at, created_at
            ) VALUES ($1, $2, $3, $4, $5, 0, 0, NOW(), NOW())
            ON CONFLICT (url_pattern, element_name)
            DO UPDATE SET
                selector = EXCLUDED.selector,
                strategy = EXCLUDED.strategy,
                confidence = EXCLUDED.confidence,
                last_verified_at = NOW(),
                miss_count = 0
            """,
            url_pattern,
            element,
            selector,
            strategy,
            confidence,
        )

        # Save to Redis (warm cache)
        await self._save_to_redis(url, element, selector, confidence, strategy, context, stable)

        # Store DOM hash for drift detection
        if dom_hash:
            await self._save_dom_hash(url, element, dom_hash)

        logger.info(
            f"[CACHE] 💾 SAVED (STABLE): {element} → {selector[:50]} "
            f"(strategy: {strategy}, stable=✓)"
        )

    async def invalidate_selector(self, url: str, element: str):
        """
        Invalidate selector in both caches.

        Used when:
        - Drift detected (DOM hash changed > threshold)
        - 2 consecutive misses
        - Explicit invalidation

        Args:
            url: Page URL
            element: Element name
        """
        url_pattern = self._normalize_url(url)

        # Delete from Redis
        redis_key = self._redis_key(url, element)
        await self.cache.delete(redis_key)

        # Delete from Postgres
        await self.db.execute(
            """
            DELETE FROM selector_cache
            WHERE url_pattern = $1 AND element_name = $2
            """,
            url_pattern,
            element,
        )

        # Delete DOM hash
        dom_hash_key = self._dom_hash_key(url, element)
        await self.cache.delete(dom_hash_key)

        await self._record_metric("cache_invalidated")
        logger.info(f"[CACHE] 🗑️ Invalidated: {element}")

    async def get_cache_stats(self) -> Dict[str, Any]:
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
        """
        redis_hits = await self._get_metric("cache_hit_redis")
        postgres_hits = await self._get_metric("cache_hit_postgres")
        misses = await self._get_metric("cache_miss")
        drift = await self._get_metric("drift_detected")
        invalidations = await self._get_metric("cache_invalidated")

        total_requests = redis_hits + postgres_hits + misses
        hit_rate = (
            (redis_hits + postgres_hits) / total_requests * 100
            if total_requests > 0
            else 0.0
        )

        # Get total cached entries from Postgres
        total_cached = await self.db.fetchval(
            "SELECT COUNT(*) FROM selector_cache"
        )

        return {
            "redis_hits": redis_hits,
            "postgres_hits": postgres_hits,
            "misses": misses,
            "hit_rate": round(hit_rate, 2),
            "drift_detections": drift,
            "invalidations": invalidations,
            "total_cached": total_cached or 0,
        }

    async def healthcheck(self) -> bool:
        """Check if cache is healthy."""
        try:
            # Test Redis
            redis_ok = await self.cache.healthcheck()

            # Test Postgres
            db_ok = await self.db.healthcheck()

            return redis_ok and db_ok
        except Exception as e:
            logger.error(f"[CACHE] Healthcheck failed: {e}")
            return False

    # ==========================================================================
    # Private Methods - Redis Layer
    # ==========================================================================

    async def _get_from_redis(
        self, url: str, element: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get selector from Redis."""
        key = self._redis_key(url, element, context)
        data = await self.cache.get_json(key)

        if data:
            logger.debug(f"[CACHE] Redis HIT: {element}")
            return data

        logger.debug(f"[CACHE] Redis MISS: {element}")
        return None

    async def _save_to_redis(
        self, url: str, element: str, selector: str, confidence: float, strategy: str, context: Optional[Dict[str, Any]] = None, stable: bool = False
    ):
        """Save selector to Redis with TTL."""
        key = self._redis_key(url, element, context)
        data = {
            "selector": selector,
            "confidence": confidence,
            "strategy": strategy,
            "last_verified": datetime.now().timestamp(),
            "stable": stable,  # Week 4: Track selector stability
        }
        await self.cache.set_json(key, data, ttl=self._redis_ttl)

    def _redis_key(self, url: str, element: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Redis key with session scope.

        Week 3 Patch: Includes session scope to prevent cross-session ID reuse.
        """
        url_pattern = self._normalize_url(url)
        session_scope = _session_key(context)
        return f"pom:{url_pattern}:{element}:{session_scope}"

    # ==========================================================================
    # Private Methods - Postgres Layer
    # ==========================================================================

    async def _get_from_postgres(
        self, url: str, element: str
    ) -> Optional[Dict[str, Any]]:
        """Get selector from Postgres."""
        url_pattern = self._normalize_url(url)

        row = await self.db.fetchrow(
            """
            SELECT selector, strategy, confidence, last_verified_at
            FROM selector_cache
            WHERE url_pattern = $1 AND element_name = $2
              AND last_verified_at > NOW() - INTERVAL '1 day' * $3
            ORDER BY hit_count DESC
            LIMIT 1
            """,
            url_pattern,
            element,
            self._postgres_retention_days,
        )

        if row:
            # Update hit count
            await self.db.execute(
                """
                UPDATE selector_cache
                SET hit_count = hit_count + 1,
                    last_verified_at = NOW(),
                    miss_count = 0
                WHERE url_pattern = $1 AND element_name = $2
                """,
                url_pattern,
                element,
            )

            logger.debug(f"[CACHE] Postgres HIT: {element}")
            return {
                "selector": row["selector"],
                "strategy": row["strategy"],
                "confidence": float(row["confidence"]),
                "last_verified": row["last_verified_at"].timestamp(),
            }

        logger.debug(f"[CACHE] Postgres MISS: {element}")
        return None

    async def _increment_miss_count(self, url: str, element: str):
        """
        Increment miss count in Postgres.

        If miss_count >= 2, invalidate cache (drift suspected).
        """
        url_pattern = self._normalize_url(url)

        result = await self.db.fetchrow(
            """
            UPDATE selector_cache
            SET miss_count = miss_count + 1
            WHERE url_pattern = $1 AND element_name = $2
            RETURNING miss_count
            """,
            url_pattern,
            element,
        )

        if result and result["miss_count"] >= 2:
            logger.warning(
                f"[CACHE] 2 consecutive misses for {element}, invalidating"
            )
            await self.invalidate_selector(url, element)

    # ==========================================================================
    # Private Methods - Drift Detection
    # ==========================================================================

    async def _check_drift(self, url: str, element: str, current_hash: str) -> bool:
        """
        Check if DOM has drifted beyond threshold.

        Args:
            url: Page URL
            element: Element name
            current_hash: Current DOM hash

        Returns:
            True if drift detected (Δ > threshold), False otherwise
        """
        cached_hash = await self._get_dom_hash(url, element)
        if not cached_hash:
            return False

        # Calculate Hamming distance as percentage
        drift_pct = self._calculate_hash_distance(cached_hash, current_hash)

        # Day 9 fix: Adaptive threshold for Salesforce Lightning
        # Lightning SPAs have 90%+ DOM volatility, use higher threshold
        threshold = self._drift_threshold
        is_sf = False
        try:
            from ..runtime.salesforce_helpers import is_lightning
            host = urlparse(url).hostname or ""
            is_sf = is_lightning(host)
            if is_sf:
                # Salesforce-specific threshold from env (default 75%)
                sf_threshold = float(os.getenv("PACTS_SF_DRIFT_THRESHOLD", "0.75")) * 100
                threshold = max(threshold, sf_threshold)
        except Exception:
            pass  # Soft-fail - use default threshold

        # Week 3 Patch: Log drift decision for every cache read
        decision = "invalidate" if drift_pct > threshold else "reuse"
        cache_key = f"{element}|{self._normalize_url(url)}"
        logger.info(
            f"[CACHE][DRIFT] key={cache_key} drift={drift_pct:.3f}% threshold={threshold:.2f}% decision={decision} is_sf={is_sf}"
        )

        if drift_pct > threshold:
            return True

        return False

    async def _save_dom_hash(self, url: str, element: str, dom_hash: str):
        """Save DOM hash for drift detection."""
        key = self._dom_hash_key(url, element)
        await self.cache.set(key, dom_hash, ttl=self._redis_ttl)

    async def _get_dom_hash(self, url: str, element: str) -> Optional[str]:
        """Get cached DOM hash."""
        key = self._dom_hash_key(url, element)
        return await self.cache.get(key)

    def _dom_hash_key(self, url: str, element: str) -> str:
        """Generate DOM hash key."""
        url_pattern = self._normalize_url(url)
        return f"dom_hash:{url_pattern}:{element}"

    def _calculate_hash_distance(self, hash1: str, hash2: str) -> float:
        """
        Calculate Hamming distance between two hashes as percentage.

        Args:
            hash1: First hash
            hash2: Second hash

        Returns:
            Percentage difference (0-100)
        """
        if len(hash1) != len(hash2):
            return 100.0

        differences = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        return (differences / len(hash1)) * 100

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL to pattern for cache lookup.

        Examples:
            https://app.com/users/123 → https://app.com/users/%
            https://app.com/page?id=5 → https://app.com/page%

        Args:
            url: Full URL

        Returns:
            Normalized URL pattern
        """
        # Remove query parameters
        if "?" in url:
            url = url.split("?")[0]

        # Remove trailing IDs/hashes (common pattern)
        # e.g., /users/123 → /users/%
        parts = url.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            parts[-1] = "%"
            return "/".join(parts)

        return url + "%"
