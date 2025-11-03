"""
Metrics API - Telemetry endpoint for PACTS (Day 12 Part B)

Exposes cache, healing, and run metrics for monitoring and dashboards.
No DB logic here - just calls storage APIs.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/cache")
async def get_cache_metrics() -> Dict[str, Any]:
    """
    Get selector cache statistics.

    Returns:
        {
            "redis_hits": int,
            "postgres_hits": int,
            "misses": int,
            "hit_rate": float,
            "total_cached": int
        }
    """
    from ..storage.init import get_storage

    try:
        storage = await get_storage()
        if not storage or not storage.selector_cache:
            return {"error": "Storage not initialized"}

        stats = await storage.selector_cache.get_cache_stats()
        return stats

    except Exception as e:
        logger.error(f"[METRICS] Cache metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heal")
async def get_heal_metrics() -> Dict[str, Any]:
    """
    Get healing strategy statistics.

    Returns:
        {
            "strategies": [
                {
                    "strategy": str,
                    "total_success": int,
                    "total_failure": int,
                    "success_rate": float,
                    "usage_count": int
                }
            ]
        }
    """
    from ..storage.init import get_storage

    try:
        storage = await get_storage()
        if not storage or not storage.heal_history:
            return {"error": "Storage not initialized"}

        strategies = await storage.heal_history.get_all_strategies()
        return {"strategies": strategies}

    except Exception as e:
        logger.error(f"[METRICS] Heal metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs")
async def get_run_metrics() -> Dict[str, Any]:
    """
    Get run statistics.

    Returns:
        {
            "total_runs": int,
            "passed": int,
            "failed": int,
            "success_rate": float,
            "avg_heal_rounds": float,
            "avg_duration_ms": float
        }
    """
    from ..storage.init import get_storage

    try:
        storage = await get_storage()
        if not storage or not storage.runs:
            return {"error": "Storage not initialized"}

        stats = await storage.runs.get_run_stats()
        return stats

    except Exception as e:
        logger.error(f"[METRICS] Run metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """
    Get combined metrics summary from all storage classes.

    Returns:
        {
            "cache": {...},
            "heal": {...},
            "runs": {...}
        }
    """
    from ..storage.init import get_storage

    try:
        storage = await get_storage()
        if not storage:
            return {"error": "Storage not initialized"}

        summary = {}

        # Cache metrics
        if storage.selector_cache:
            summary["cache"] = await storage.selector_cache.get_cache_stats()

        # Heal metrics
        if storage.heal_history:
            strategies = await storage.heal_history.get_all_strategies()
            summary["heal"] = {
                "strategy_count": len(strategies),
                "top_strategies": strategies[:5] if strategies else []
            }

        # Run metrics
        if storage.runs:
            summary["runs"] = await storage.runs.get_run_stats()

        return summary

    except Exception as e:
        logger.error(f"[METRICS] Summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
