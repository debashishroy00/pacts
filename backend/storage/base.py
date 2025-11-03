"""
Base storage pattern for uniform async operations and metrics.

All storage classes (SelectorCache, HealHistory, RunStorage) inherit from BaseStorage
to ensure consistent patterns for retry logic, metrics, and context management.
"""

import os
import logging
from typing import Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """
    Base class for all storage operations.

    Provides:
    - Async context management
    - Consistent retry logic
    - Automatic metrics collection
    - Standardized error handling
    """

    def __init__(self, db, cache):
        """
        Initialize storage with database and cache.

        Args:
            db: Database instance (asyncpg pool)
            cache: Cache instance (Redis)
        """
        self.db = db
        self.cache = cache
        self._metrics_enabled = os.getenv("ENABLE_MEMORY", "true").lower() == "true"

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type:
            logger.error(f"[{self.__class__.__name__}] Error in context: {exc_val}")
        return False  # Don't suppress exceptions

    async def _record_metric(self, metric_name: str, value: float = 1.0):
        """
        Record metric to Redis counter.

        Metrics are stored as:
        - Key: metrics:{class_name}:{metric_name}
        - Value: Counter
        - TTL: 24 hours (rolling window)

        Args:
            metric_name: Name of metric (e.g., 'cache_hit', 'cache_miss')
            value: Metric value (default 1.0 for counters)
        """
        if not self._metrics_enabled:
            return

        try:
            class_name = self.__class__.__name__.lower()
            key = f"metrics:{class_name}:{metric_name}"

            await self.cache.incr(key, int(value))

            # Set 24-hour TTL on first increment
            ttl = await self.cache.ttl(key)
            if ttl == -1:  # No TTL set
                await self.cache.expire(key, 86400)

        except Exception as e:
            # Don't fail operations due to metrics
            logger.warning(f"[{self.__class__.__name__}] Failed to record metric: {e}")

    async def _get_metric(self, metric_name: str) -> int:
        """
        Get current metric value.

        Args:
            metric_name: Name of metric

        Returns:
            Current counter value (0 if not exists)
        """
        try:
            class_name = self.__class__.__name__.lower()
            key = f"metrics:{class_name}:{metric_name}"
            value = await self.cache.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.warning(f"[{self.__class__.__name__}] Failed to get metric: {e}")
            return 0

    async def get_metrics_summary(self) -> dict:
        """
        Get summary of all metrics for this storage class.

        Returns:
            Dictionary of metric_name: value
        """
        try:
            class_name = self.__class__.__name__.lower()
            pattern = f"metrics:{class_name}:*"
            keys = await self.cache.keys(pattern)

            summary = {}
            for key in keys:
                metric_name = key.split(":")[-1]
                value = await self.cache.get(key)
                summary[metric_name] = int(value) if value else 0

            return summary
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Failed to get metrics summary: {e}")
            return {}

    @abstractmethod
    async def healthcheck(self) -> bool:
        """
        Check if storage is healthy.

        Must be implemented by subclasses.

        Returns:
            True if healthy, False otherwise
        """
        pass
