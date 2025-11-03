"""
Healing History - Track healing strategy success rates.

Records which strategies work best for specific elements/pages to prioritize
healing attempts in future failures.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import BaseStorage

logger = logging.getLogger(__name__)


class HealHistory(BaseStorage):
    """
    Manages healing strategy success tracking.

    Telemetry Counters:
    - heal_success: Successful healing
    - heal_failure: Failed healing
    - strategy_used: Strategy attempted
    """

    def __init__(self, db, cache):
        super().__init__(db, cache)

    # ==========================================================================
    # Public API
    # ==========================================================================

    async def record_outcome(
        self,
        element: str,
        url: str,
        strategy: str,
        success: bool,
        heal_time_ms: int,
    ):
        """
        Record healing attempt outcome.

        Args:
            element: Element name
            url: Page URL
            strategy: Healing strategy used
            success: True if healing succeeded
            heal_time_ms: Time taken in milliseconds
        """
        url_pattern = self._normalize_url(url)

        # Upsert healing history
        await self.db.execute(
            """
            INSERT INTO heal_history (
                element_name, url_pattern, strategy,
                success_count, failure_count, avg_heal_time_ms, last_used_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (element_name, url_pattern, strategy)
            DO UPDATE SET
                success_count = heal_history.success_count + $4,
                failure_count = heal_history.failure_count + $5,
                avg_heal_time_ms = (
                    COALESCE(heal_history.avg_heal_time_ms, 0) *
                    (heal_history.success_count + heal_history.failure_count) +
                    $6
                ) / (heal_history.success_count + heal_history.failure_count + 1),
                last_used_at = NOW()
            """,
            element,
            url_pattern,
            strategy,
            1 if success else 0,
            0 if success else 1,
            heal_time_ms,
        )

        # Record metrics
        if success:
            await self._record_metric("heal_success")
            logger.info(
                f"[HEAL] ✅ {strategy} succeeded for {element} ({heal_time_ms}ms)"
            )
        else:
            await self._record_metric("heal_failure")
            logger.info(f"[HEAL] ❌ {strategy} failed for {element}")

        await self._record_metric("strategy_used")

        # Cache recent outcome for fast lookup
        await self._cache_recent_outcome(element, url_pattern, strategy, success)

    async def get_best_strategy(
        self, element: str, url: str, top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get best healing strategies based on historical success rate.

        Args:
            element: Element name
            url: Page URL
            top_n: Number of top strategies to return

        Returns:
            List of {
                "strategy": str,
                "success_rate": float,
                "success_count": int,
                "failure_count": int,
                "avg_heal_time_ms": int
            }
        """
        url_pattern = self._normalize_url(url)

        # Try cache first (recent outcomes)
        cached = await self._get_cached_best_strategy(element, url_pattern)
        if cached:
            return cached[:top_n]

        # Query Postgres for historical data
        rows = await self.db.fetch(
            """
            SELECT
                strategy,
                success_count,
                failure_count,
                avg_heal_time_ms,
                ROUND(
                    success_count::numeric / NULLIF(success_count + failure_count, 0) * 100,
                    2
                ) AS success_rate
            FROM heal_history
            WHERE element_name = $1 AND url_pattern LIKE $2
            ORDER BY success_rate DESC, success_count DESC
            LIMIT $3
            """,
            element,
            url_pattern,
            top_n,
        )

        results = [
            {
                "strategy": row["strategy"],
                "success_rate": float(row["success_rate"] or 0.0),
                "success_count": row["success_count"],
                "failure_count": row["failure_count"],
                "avg_heal_time_ms": row["avg_heal_time_ms"],
            }
            for row in rows
        ]

        # Cache results for 5 minutes
        if results:
            await self._cache_best_strategy(element, url_pattern, results)

        return results

    async def get_success_rate(self, element: str, url: str, strategy: str) -> float:
        """
        Get success rate for specific element + strategy.

        Args:
            element: Element name
            url: Page URL
            strategy: Healing strategy

        Returns:
            Success rate as percentage (0-100)
        """
        url_pattern = self._normalize_url(url)

        row = await self.db.fetchrow(
            """
            SELECT
                success_count,
                failure_count,
                ROUND(
                    success_count::numeric / NULLIF(success_count + failure_count, 0) * 100,
                    2
                ) AS success_rate
            FROM heal_history
            WHERE element_name = $1
              AND url_pattern = $2
              AND strategy = $3
            """,
            element,
            url_pattern,
            strategy,
        )

        if row:
            return float(row["success_rate"] or 0.0)

        return 0.0

    async def get_all_strategies(self) -> List[Dict[str, Any]]:
        """
        Get all healing strategies with aggregated stats.

        Returns:
            List of {
                "strategy": str,
                "total_success": int,
                "total_failure": int,
                "success_rate": float,
                "usage_count": int
            }
        """
        rows = await self.db.fetch(
            """
            SELECT
                strategy,
                SUM(success_count) AS total_success,
                SUM(failure_count) AS total_failure,
                ROUND(
                    SUM(success_count)::numeric / NULLIF(SUM(success_count + failure_count), 0) * 100,
                    2
                ) AS success_rate,
                COUNT(*) AS usage_count
            FROM heal_history
            GROUP BY strategy
            ORDER BY success_rate DESC, total_success DESC
            """
        )

        return [
            {
                "strategy": row["strategy"],
                "total_success": row["total_success"],
                "total_failure": row["total_failure"],
                "success_rate": float(row["success_rate"] or 0.0),
                "usage_count": row["usage_count"],
            }
            for row in rows
        ]

    async def get_element_stats(self, element: str) -> List[Dict[str, Any]]:
        """
        Get healing stats for specific element across all pages.

        Args:
            element: Element name

        Returns:
            List of strategy stats for this element
        """
        rows = await self.db.fetch(
            """
            SELECT
                strategy,
                url_pattern,
                success_count,
                failure_count,
                avg_heal_time_ms,
                ROUND(
                    success_count::numeric / NULLIF(success_count + failure_count, 0) * 100,
                    2
                ) AS success_rate,
                last_used_at
            FROM heal_history
            WHERE element_name = $1
            ORDER BY success_rate DESC, success_count DESC
            """,
            element,
        )

        return [
            {
                "strategy": row["strategy"],
                "url_pattern": row["url_pattern"],
                "success_count": row["success_count"],
                "failure_count": row["failure_count"],
                "avg_heal_time_ms": row["avg_heal_time_ms"],
                "success_rate": float(row["success_rate"] or 0.0),
                "last_used_at": row["last_used_at"].isoformat(),
            }
            for row in rows
        ]

    async def healthcheck(self) -> bool:
        """Check if heal history storage is healthy."""
        try:
            # Test Postgres
            count = await self.db.fetchval("SELECT COUNT(*) FROM heal_history")
            return count is not None
        except Exception as e:
            logger.error(f"[HEAL] Healthcheck failed: {e}")
            return False

    # ==========================================================================
    # Private Methods - Caching
    # ==========================================================================

    async def _cache_recent_outcome(
        self, element: str, url_pattern: str, strategy: str, success: bool
    ):
        """Cache recent outcome for fast lookups."""
        key = f"heal:recent:{element}:{url_pattern}"

        # Get current cache
        cached = await self.cache.get_json(key) or []

        # Add new outcome
        cached.append(
            {
                "strategy": strategy,
                "success": success,
                "timestamp": datetime.now().timestamp(),
            }
        )

        # Keep only last 10 outcomes
        cached = cached[-10:]

        # Save with 5-minute TTL
        await self.cache.set_json(key, cached, ttl=300)

    async def _cache_best_strategy(
        self, element: str, url_pattern: str, strategies: List[Dict[str, Any]]
    ):
        """Cache best strategies for fast lookups."""
        key = f"heal:best:{element}:{url_pattern}"
        await self.cache.set_json(key, strategies, ttl=300)

    async def _get_cached_best_strategy(
        self, element: str, url_pattern: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached best strategies."""
        key = f"heal:best:{element}:{url_pattern}"
        return await self.cache.get_json(key)

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL to pattern for cache lookup.

        Examples:
            https://app.com/users/123 → https://app.com/users/%
            https://app.com/page?id=5 → https://app.com/page%
        """
        # Remove query parameters
        if "?" in url:
            url = url.split("?")[0]

        # Remove trailing IDs/hashes
        parts = url.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            parts[-1] = "%"
            return "/".join(parts)

        return url + "%"
