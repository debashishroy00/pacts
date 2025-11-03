"""
Storage initialization and lifecycle management.

Handles connection setup, teardown, and health monitoring for
Postgres + Redis + storage classes.
"""

import os
import logging
import atexit
from typing import Optional, Tuple

from .database import Database, db
from .cache import Cache, cache
from .selector_cache import SelectorCache
from .heal_history import HealHistory
from .runs import RunStorage

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages storage layer lifecycle.

    Usage:
        storage = await StorageManager.initialize()
        # Use storage.selector_cache, storage.heal_history, storage.runs
        await StorageManager.shutdown()
    """

    _instance: Optional["StorageManager"] = None
    _initialized: bool = False

    def __init__(self):
        self.db = db
        self.cache = cache
        self.selector_cache: Optional[SelectorCache] = None
        self.heal_history: Optional[HealHistory] = None
        self.runs: Optional[RunStorage] = None
        self._memory_enabled = os.getenv("ENABLE_MEMORY", "true").lower() == "true"

    @classmethod
    async def initialize(cls) -> "StorageManager":
        """
        Initialize storage layer (singleton pattern).

        Returns:
            StorageManager instance
        """
        if cls._instance is not None and cls._initialized:
            logger.info("[STORAGE] Already initialized, returning existing instance")
            return cls._instance

        logger.info("[STORAGE] Initializing memory & persistence layer...")

        instance = cls()

        # Check if memory is enabled
        if not instance._memory_enabled:
            logger.warning("[STORAGE] Memory disabled (ENABLE_MEMORY=false), using no-op storage")
            cls._instance = instance
            cls._initialized = True
            return instance

        try:
            # Connect to database
            await instance.db.connect()
            logger.info("[STORAGE] ✅ Postgres connected")

            # Connect to cache
            await instance.cache.connect()
            logger.info("[STORAGE] ✅ Redis connected")

            # Initialize storage classes
            instance.selector_cache = SelectorCache(instance.db, instance.cache)
            instance.heal_history = HealHistory(instance.db, instance.cache)
            instance.runs = RunStorage(instance.db, instance.cache)

            logger.info("[STORAGE] ✅ Storage classes initialized")

            # Health check
            health = await instance.healthcheck()
            if not health["healthy"]:
                logger.error(f"[STORAGE] Health check failed: {health}")
                raise RuntimeError("Storage health check failed")

            logger.info("[STORAGE] ✅ Health check passed")

            # Register cleanup on exit
            atexit.register(lambda: instance._sync_shutdown())

            cls._instance = instance
            cls._initialized = True

            logger.info("[STORAGE] 🚀 Memory & persistence layer ready")
            return instance

        except Exception as e:
            logger.error(f"[STORAGE] ❌ Initialization failed: {e}")
            # Cleanup partial initialization
            await instance._cleanup()
            raise

    @classmethod
    async def get_instance(cls) -> Optional["StorageManager"]:
        """
        Get existing instance (must be initialized first).

        Returns:
            StorageManager instance or None
        """
        return cls._instance

    @classmethod
    async def shutdown(cls):
        """Shutdown storage layer (cleanup connections)."""
        if cls._instance is None:
            logger.info("[STORAGE] No instance to shutdown")
            return

        logger.info("[STORAGE] Shutting down...")
        await cls._instance._cleanup()
        cls._instance = None
        cls._initialized = False
        logger.info("[STORAGE] ✅ Shutdown complete")

    async def _cleanup(self):
        """Cleanup connections."""
        try:
            if self.db.pool is not None:
                await self.db.disconnect()
                logger.info("[STORAGE] Postgres disconnected")
        except Exception as e:
            logger.error(f"[STORAGE] Error disconnecting database: {e}")

        try:
            if self.cache.client is not None:
                await self.cache.disconnect()
                logger.info("[STORAGE] Redis disconnected")
        except Exception as e:
            logger.error(f"[STORAGE] Error disconnecting cache: {e}")

    def _sync_shutdown(self):
        """Synchronous shutdown for atexit handler."""
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._cleanup())
            else:
                loop.run_until_complete(self._cleanup())
        except Exception as e:
            logger.error(f"[STORAGE] Error in sync shutdown: {e}")

    async def healthcheck(self) -> dict:
        """
        Check health of all storage components.

        Returns:
            {
                "healthy": bool,
                "database": bool,
                "cache": bool,
                "selector_cache": bool,
                "heal_history": bool,
                "runs": bool
            }
        """
        if not self._memory_enabled:
            return {"healthy": True, "memory_enabled": False}

        checks = {
            "database": await self.db.healthcheck() if self.db else False,
            "cache": await self.cache.healthcheck() if self.cache else False,
            "selector_cache": (
                await self.selector_cache.healthcheck() if self.selector_cache else False
            ),
            "heal_history": (
                await self.heal_history.healthcheck() if self.heal_history else False
            ),
            "runs": await self.runs.healthcheck() if self.runs else False,
        }

        checks["healthy"] = all(checks.values())
        return checks

    async def get_metrics_summary(self) -> dict:
        """
        Get metrics summary from all storage classes.

        Returns:
            {
                "selector_cache": {...},
                "heal_history": {...},
                "runs": {...}
            }
        """
        if not self._memory_enabled:
            return {}

        summary = {}

        if self.selector_cache:
            summary["selector_cache"] = await self.selector_cache.get_metrics_summary()
            summary["cache_stats"] = await self.selector_cache.get_cache_stats()

        if self.heal_history:
            summary["heal_history"] = await self.heal_history.get_metrics_summary()

        if self.runs:
            summary["runs"] = await self.runs.get_metrics_summary()
            summary["run_stats"] = await self.runs.get_run_stats()

        return summary


# Global storage manager instance
_storage: Optional[StorageManager] = None


async def get_storage() -> Optional[StorageManager]:
    """
    Get storage manager instance (singleton).

    Returns:
        StorageManager instance or None if not initialized
    """
    global _storage

    if _storage is None:
        _storage = await StorageManager.initialize()

    return _storage


async def shutdown_storage():
    """Shutdown storage manager."""
    await StorageManager.shutdown()
