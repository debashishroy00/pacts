"""
Step Tracker - Helper for RunStorage step tracking (Day 12 Part A)

Provides simple async function to save step execution details to RunStorage.
Called from executor after each successful step.
"""

import logging
from typing import Optional
from ..storage.init import get_storage

logger = logging.getLogger(__name__)


async def track_step(
    req_id: str,
    step_idx: int,
    element: str,
    action: str,
    value: Optional[str],
    selector: Optional[str],
    strategy: Optional[str],
    confidence: Optional[float],
    outcome: str,
    heal_attempts: int,
    execution_time_ms: int,
    error_message: Optional[str] = None,
    screenshot_path: Optional[str] = None
):
    """
    Save step execution details to RunStorage.

    Args:
        req_id: Run identifier
        step_idx: Step index
        element: Element name
        action: Action performed
        value: Value used (if any)
        selector: Selector used
        strategy: Discovery strategy
        confidence: Confidence score
        outcome: 'success', 'healed', 'failed'
        heal_attempts: Number of heal attempts
        execution_time_ms: Execution time
        error_message: Error if failed
        screenshot_path: Path to screenshot
    """
    storage = await get_storage()
    if not storage or not storage.runs:
        return

    try:
        await storage.runs.save_step(
            req_id=req_id,
            step_idx=step_idx,
            element=element,
            action=action,
            value=value,
            selector=selector,
            strategy=strategy,
            confidence=confidence,
            outcome=outcome,
            heal_attempts=heal_attempts,
            execution_time_ms=execution_time_ms,
            error_message=error_message,
            screenshot_path=screenshot_path
        )
    except Exception as e:
        logger.warning(f"[TRACKER] Failed to save step: {e}")
