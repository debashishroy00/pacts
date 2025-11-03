"""
Run Storage - Persist test execution data.

Captures:
- Run metadata (req_id, status, timing)
- Step-level execution details
- Artifacts (screenshots, HTML snapshots)
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import BaseStorage

logger = logging.getLogger(__name__)


class RunStorage(BaseStorage):
    """
    Manages test run persistence.

    Telemetry Counters:
    - runs_created: Total runs started
    - runs_passed: Successful runs
    - runs_failed: Failed runs
    - steps_executed: Total steps executed
    - artifacts_saved: Total artifacts stored
    """

    def __init__(self, db, cache):
        super().__init__(db, cache)
        self._artifact_path = os.getenv("ARTIFACT_PATH", "./artifacts")

    # ==========================================================================
    # Public API - Run Management
    # ==========================================================================

    async def create_run(
        self, req_id: str, test_name: str, url: str, total_steps: int
    ) -> Dict[str, Any]:
        """
        Create new test run.

        Args:
            req_id: Unique run identifier
            test_name: Name of test
            url: Target URL
            total_steps: Expected number of steps

        Returns:
            Run metadata
        """
        await self.db.execute(
            """
            INSERT INTO runs (
                req_id, test_name, url, status, total_steps,
                completed_steps, heal_rounds, heal_events, start_time
            ) VALUES ($1, $2, $3, 'running', $4, 0, 0, 0, NOW())
            """,
            req_id,
            test_name,
            url,
            total_steps,
        )

        await self._record_metric("runs_created")

        logger.info(f"[RUN] 🚀 Created run: {req_id} ({test_name})")

        return {
            "req_id": req_id,
            "test_name": test_name,
            "url": url,
            "status": "running",
            "total_steps": total_steps,
        }

    async def update_run(
        self,
        req_id: str,
        status: str,
        completed_steps: Optional[int] = None,
        heal_rounds: Optional[int] = None,
        heal_events: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """
        Update run status and metrics.

        Args:
            req_id: Run identifier
            status: 'running', 'pass', 'fail', 'error'
            completed_steps: Number of completed steps
            heal_rounds: Number of heal rounds used
            heal_events: Number of heal events
            error_message: Error message if failed
        """
        # Build dynamic update query
        updates = ["status = $2"]
        params = [req_id, status]
        param_idx = 3

        if completed_steps is not None:
            updates.append(f"completed_steps = ${param_idx}")
            params.append(completed_steps)
            param_idx += 1

        if heal_rounds is not None:
            updates.append(f"heal_rounds = ${param_idx}")
            params.append(heal_rounds)
            param_idx += 1

        if heal_events is not None:
            updates.append(f"heal_events = ${param_idx}")
            params.append(heal_events)
            param_idx += 1

        if error_message is not None:
            updates.append(f"error_message = ${param_idx}")
            params.append(error_message)
            param_idx += 1

        # Add end_time and duration if finishing
        if status in ["pass", "fail", "error"]:
            updates.append("end_time = NOW()")
            updates.append(
                "duration_ms = EXTRACT(EPOCH FROM (NOW() - start_time)) * 1000"
            )

        query = f"""
            UPDATE runs
            SET {', '.join(updates)}
            WHERE req_id = $1
        """

        await self.db.execute(query, *params)

        # Record metrics
        if status == "pass":
            await self._record_metric("runs_passed")
        elif status in ["fail", "error"]:
            await self._record_metric("runs_failed")

        logger.info(f"[RUN] Updated: {req_id} → {status}")

    async def get_run(self, req_id: str) -> Optional[Dict[str, Any]]:
        """
        Get run details.

        Args:
            req_id: Run identifier

        Returns:
            Run metadata or None
        """
        row = await self.db.fetchrow(
            """
            SELECT
                req_id, test_name, url, status, total_steps, completed_steps,
                heal_rounds, heal_events, start_time, end_time, duration_ms,
                error_message, created_at
            FROM runs
            WHERE req_id = $1
            """,
            req_id,
        )

        if not row:
            return None

        return {
            "req_id": row["req_id"],
            "test_name": row["test_name"],
            "url": row["url"],
            "status": row["status"],
            "total_steps": row["total_steps"],
            "completed_steps": row["completed_steps"],
            "heal_rounds": row["heal_rounds"],
            "heal_events": row["heal_events"],
            "start_time": row["start_time"].isoformat(),
            "end_time": row["end_time"].isoformat() if row["end_time"] else None,
            "duration_ms": row["duration_ms"],
            "error_message": row["error_message"],
            "created_at": row["created_at"].isoformat(),
        }

    # ==========================================================================
    # Public API - Step Management
    # ==========================================================================

    async def save_step(
        self,
        req_id: str,
        step_idx: int,
        element: str,
        action: str,
        value: Optional[str],
        selector: Optional[str],
        strategy: Optional[str],
        confidence: Optional[float],
        outcome: str,
        heal_attempts: int = 0,
        execution_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        screenshot_path: Optional[str] = None,
    ):
        """
        Save step execution details.

        Args:
            req_id: Run identifier
            step_idx: Step index
            element: Element name
            action: Action (click, fill, select, etc.)
            value: Value for action
            selector: Selector used
            strategy: Discovery strategy
            confidence: Confidence score
            outcome: 'success', 'healed', 'failed'
            heal_attempts: Number of heal attempts
            execution_time_ms: Execution time
            error_message: Error if failed
            screenshot_path: Path to screenshot
        """
        await self.db.execute(
            """
            INSERT INTO run_steps (
                req_id, step_idx, element, action, value, selector, strategy,
                confidence, outcome, heal_attempts, execution_time_ms,
                error_message, screenshot_path
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (req_id, step_idx)
            DO UPDATE SET
                outcome = EXCLUDED.outcome,
                heal_attempts = EXCLUDED.heal_attempts,
                execution_time_ms = EXCLUDED.execution_time_ms,
                error_message = EXCLUDED.error_message,
                screenshot_path = EXCLUDED.screenshot_path
            """,
            req_id,
            step_idx,
            element,
            action,
            value,
            selector,
            strategy,
            confidence,
            outcome,
            heal_attempts,
            execution_time_ms,
            error_message,
            screenshot_path,
        )

        await self._record_metric("steps_executed")

        logger.debug(
            f"[RUN] Step {step_idx}: {element} → {outcome} ({execution_time_ms}ms)"
        )

    async def get_steps(self, req_id: str) -> List[Dict[str, Any]]:
        """
        Get all steps for run.

        Args:
            req_id: Run identifier

        Returns:
            List of step details
        """
        rows = await self.db.fetch(
            """
            SELECT
                step_idx, element, action, value, selector, strategy, confidence,
                outcome, heal_attempts, execution_time_ms, error_message,
                screenshot_path, created_at
            FROM run_steps
            WHERE req_id = $1
            ORDER BY step_idx ASC
            """,
            req_id,
        )

        return [
            {
                "step_idx": row["step_idx"],
                "element": row["element"],
                "action": row["action"],
                "value": row["value"],
                "selector": row["selector"],
                "strategy": row["strategy"],
                "confidence": float(row["confidence"]) if row["confidence"] else None,
                "outcome": row["outcome"],
                "heal_attempts": row["heal_attempts"],
                "execution_time_ms": row["execution_time_ms"],
                "error_message": row["error_message"],
                "screenshot_path": row["screenshot_path"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]

    # ==========================================================================
    # Public API - Artifact Management
    # ==========================================================================

    async def save_artifact(
        self,
        req_id: str,
        step_idx: Optional[int],
        artifact_type: str,
        file_path: str,
        file_size: int,
        content_hash: Optional[str] = None,
    ):
        """
        Save artifact reference.

        Args:
            req_id: Run identifier
            step_idx: Step index (None for run-level artifacts)
            artifact_type: 'screenshot', 'html', 'dom_hash'
            file_path: Path to artifact file
            file_size: File size in bytes
            content_hash: SHA256 hash of content
        """
        await self.db.execute(
            """
            INSERT INTO artifacts (
                req_id, step_idx, artifact_type, file_path, file_size, content_hash
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            req_id,
            step_idx,
            artifact_type,
            file_path,
            file_size,
            content_hash,
        )

        await self._record_metric("artifacts_saved")

        logger.debug(f"[RUN] Artifact saved: {artifact_type} ({file_size} bytes)")

    async def get_artifacts(
        self, req_id: str, artifact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get artifacts for run.

        Args:
            req_id: Run identifier
            artifact_type: Filter by type (optional)

        Returns:
            List of artifact details
        """
        if artifact_type:
            rows = await self.db.fetch(
                """
                SELECT
                    id, step_idx, artifact_type, file_path, file_size,
                    content_hash, created_at
                FROM artifacts
                WHERE req_id = $1 AND artifact_type = $2
                ORDER BY created_at ASC
                """,
                req_id,
                artifact_type,
            )
        else:
            rows = await self.db.fetch(
                """
                SELECT
                    id, step_idx, artifact_type, file_path, file_size,
                    content_hash, created_at
                FROM artifacts
                WHERE req_id = $1
                ORDER BY created_at ASC
                """,
                req_id,
            )

        return [
            {
                "id": row["id"],
                "step_idx": row["step_idx"],
                "artifact_type": row["artifact_type"],
                "file_path": row["file_path"],
                "file_size": row["file_size"],
                "content_hash": row["content_hash"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]

    # ==========================================================================
    # Public API - Queries
    # ==========================================================================

    async def get_recent_runs(
        self, limit: int = 100, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent test runs.

        Args:
            limit: Maximum number of runs
            status: Filter by status (optional)

        Returns:
            List of run summaries
        """
        if status:
            rows = await self.db.fetch(
                """
                SELECT
                    req_id, test_name, status, completed_steps, total_steps,
                    heal_rounds, duration_ms, start_time
                FROM runs
                WHERE status = $1
                ORDER BY start_time DESC
                LIMIT $2
                """,
                status,
                limit,
            )
        else:
            rows = await self.db.fetch(
                """
                SELECT
                    req_id, test_name, status, completed_steps, total_steps,
                    heal_rounds, duration_ms, start_time
                FROM runs
                ORDER BY start_time DESC
                LIMIT $1
                """,
                limit,
            )

        return [
            {
                "req_id": row["req_id"],
                "test_name": row["test_name"],
                "status": row["status"],
                "progress": f"{row['completed_steps']}/{row['total_steps']}",
                "heal_rounds": row["heal_rounds"],
                "duration_ms": row["duration_ms"],
                "start_time": row["start_time"].isoformat(),
            }
            for row in rows
        ]

    async def get_run_stats(self) -> Dict[str, Any]:
        """
        Get overall run statistics.

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
        row = await self.db.fetchrow(
            """
            SELECT
                COUNT(*) AS total_runs,
                COUNT(*) FILTER (WHERE status = 'pass') AS passed,
                COUNT(*) FILTER (WHERE status = 'fail') AS failed,
                ROUND(
                    COUNT(*) FILTER (WHERE status = 'pass')::numeric / NULLIF(COUNT(*), 0) * 100,
                    2
                ) AS success_rate,
                ROUND(AVG(heal_rounds)::numeric, 2) AS avg_heal_rounds,
                ROUND(AVG(duration_ms)::numeric, 0) AS avg_duration_ms
            FROM runs
            WHERE status IN ('pass', 'fail')
            """
        )

        if not row:
            return {
                "total_runs": 0,
                "passed": 0,
                "failed": 0,
                "success_rate": 0.0,
                "avg_heal_rounds": 0.0,
                "avg_duration_ms": 0.0,
            }

        return {
            "total_runs": row["total_runs"],
            "passed": row["passed"],
            "failed": row["failed"],
            "success_rate": float(row["success_rate"] or 0.0),
            "avg_heal_rounds": float(row["avg_heal_rounds"] or 0.0),
            "avg_duration_ms": float(row["avg_duration_ms"] or 0.0),
        }

    async def healthcheck(self) -> bool:
        """Check if run storage is healthy."""
        try:
            # Test Postgres
            count = await self.db.fetchval("SELECT COUNT(*) FROM runs")
            return count is not None
        except Exception as e:
            logger.error(f"[RUN] Healthcheck failed: {e}")
            return False
