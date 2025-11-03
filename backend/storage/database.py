"""
Database connection and pooling for Postgres.

Uses asyncpg for async Postgres operations with connection pooling.
"""

import os
import asyncpg
from typing import Optional
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class Database:
    """Postgres database connection manager with pooling."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load database configuration from environment."""
        return {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DB", "pacts"),
            "user": os.getenv("POSTGRES_USER", "pacts_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "pacts_dev_password"),
            "min_size": int(os.getenv("POSTGRES_POOL_MIN_SIZE", "5")),
            "max_size": int(os.getenv("POSTGRES_POOL_MAX_SIZE", "20")),
            "command_timeout": int(os.getenv("QUERY_TIMEOUT", "10")),
        }

    async def connect(self):
        """Create connection pool."""
        if self.pool is not None:
            logger.warning("[DB] Pool already exists, skipping connection")
            return

        try:
            self.pool = await asyncpg.create_pool(
                host=self._config["host"],
                port=self._config["port"],
                database=self._config["database"],
                user=self._config["user"],
                password=self._config["password"],
                min_size=self._config["min_size"],
                max_size=self._config["max_size"],
                command_timeout=self._config["command_timeout"],
            )
            logger.info(
                f"[DB] ✅ Connected to Postgres: {self._config['database']} "
                f"(pool: {self._config['min_size']}-{self._config['max_size']})"
            )
        except Exception as e:
            logger.error(f"[DB] ❌ Failed to connect: {e}")
            raise

    async def disconnect(self):
        """Close connection pool."""
        if self.pool is not None:
            await self.pool.close()
            logger.info("[DB] Connection pool closed")
            self.pool = None

    async def execute(self, query: str, *args):
        """Execute a query (INSERT, UPDATE, DELETE)."""
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Fetch multiple rows."""
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Fetch a single row."""
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Fetch a single value."""
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def healthcheck(self) -> bool:
        """Check if database connection is healthy."""
        try:
            result = await self.fetchval("SELECT 1")
            return result == 1
        except Exception as e:
            logger.error(f"[DB] Healthcheck failed: {e}")
            return False


# Global database instance
db = Database()
