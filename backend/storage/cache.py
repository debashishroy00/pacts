"""
Redis cache layer for ephemeral state.

Handles POM cache, LangGraph checkpoints, healing counters, and rate limiting.
"""

import os
import time
import json
import redis.asyncio as redis
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class Cache:
    """Redis cache manager for fast ephemeral state."""

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load Redis configuration from environment."""
        return {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "db": int(os.getenv("REDIS_DB", "0")),
            "password": os.getenv("REDIS_PASSWORD") or None,
            "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
            "decode_responses": True,  # Auto-decode bytes to strings
        }

    async def connect(self):
        """Create Redis connection."""
        if self.client is not None:
            logger.warning("[CACHE] Client already exists, skipping connection")
            return

        try:
            self.client = redis.Redis(
                host=self._config["host"],
                port=self._config["port"],
                db=self._config["db"],
                password=self._config["password"],
                max_connections=self._config["max_connections"],
                decode_responses=self._config["decode_responses"],
            )

            # Test connection
            await self.client.ping()
            logger.info(
                f"[CACHE] ✅ Connected to Redis: {self._config['host']}:{self._config['port']}"
            )
        except Exception as e:
            logger.error(f"[CACHE] ❌ Failed to connect: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection."""
        if self.client is not None:
            await self.client.close()
            logger.info("[CACHE] Connection closed")
            self.client = None

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if self.client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")

        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None):
        """Set value in cache with optional TTL (seconds)."""
        if self.client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")

        if ttl:
            await self.client.setex(key, ttl, value)
        else:
            await self.client.set(key, value)

    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"[CACHE] Invalid JSON for key: {key}")
                return None
        return None

    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None):
        """Set JSON value in cache."""
        await self.set(key, json.dumps(value), ttl)

    async def delete(self, key: str):
        """Delete key from cache."""
        if self.client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")

        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if self.client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")

        return bool(await self.client.exists(key))

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        if self.client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")

        return await self.client.incrby(key, amount)

    async def expire(self, key: str, ttl: int):
        """Set TTL on existing key."""
        if self.client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")

        await self.client.expire(key, ttl)

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for key (-1 if no TTL, -2 if not exists)."""
        if self.client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")

        return await self.client.ttl(key)

    async def keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern."""
        if self.client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")

        return await self.client.keys(pattern)

    async def flush_db(self):
        """Flush current database (USE WITH CAUTION)."""
        if self.client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")

        await self.client.flushdb()
        logger.warning("[CACHE] Database flushed")

    async def healthcheck(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            return await self.client.ping()
        except Exception as e:
            logger.error(f"[CACHE] Healthcheck failed: {e}")
            return False

    # ==========================================================================
    # POM Cache Helper Methods
    # ==========================================================================

    async def get_pom(self, url: str, element: str) -> Optional[dict]:
        """Get POM entry from cache."""
        key = f"pom:{url}:{element}"
        return await self.get_json(key)

    async def set_pom(
        self, url: str, element: str, selector: str, confidence: float, strategy: str
    ):
        """Set POM entry in cache (1-hour TTL)."""
        key = f"pom:{url}:{element}"
        value = {
            "selector": selector,
            "confidence": confidence,
            "strategy": strategy,
            "last_verified": int(time.time()),
        }
        ttl = int(os.getenv("REDIS_CACHE_TTL", "3600"))
        await self.set_json(key, value, ttl)

    # ==========================================================================
    # Healing Counter Helper Methods
    # ==========================================================================

    async def get_heal_count(self, req_id: str, selector: str) -> int:
        """Get heal attempt count for selector."""
        key = f"heal:{req_id}:{selector}"
        value = await self.get(key)
        return int(value) if value else 0

    async def incr_heal_count(self, req_id: str, selector: str) -> int:
        """Increment heal counter (1-hour TTL)."""
        key = f"heal:{req_id}:{selector}"
        count = await self.incr(key)

        # Set TTL on first increment
        if count == 1:
            await self.expire(key, 3600)

        return count

    # ==========================================================================
    # Rate Limiting Helper Methods
    # ==========================================================================

    async def check_rate_limit(self, client_id: str, limit: int = 100) -> bool:
        """Check if client is within rate limit (requests per minute)."""
        key = f"rate:{client_id}"
        count = await self.get(key)

        if count is None:
            # First request - set counter with 60s TTL
            await self.set(key, "1", 60)
            return True

        if int(count) >= limit:
            return False

        await self.incr(key)
        return True


# Global cache instance
cache = Cache()
