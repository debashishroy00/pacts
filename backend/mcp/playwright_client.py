"""
MCP Playwright Client - Async wrapper for MCP Playwright server.

This module provides a clean interface to MCP Playwright for:
- Locator discovery with native Playwright semantics
- Actionability assertions (unique, visible, enabled, stable)
- Reveal actions (scroll, overlay dismiss, network idle)
- Reprobe with fallback chains (role → label → testId → css)
- Debug probes with full diagnostic context

Gracefully falls back to local strategies when MCP unavailable.
"""

import os
import logging
import aiohttp
from typing import Dict, Any, Optional, List
from functools import lru_cache

logger = logging.getLogger(__name__)

# Environment configuration
USE_MCP = os.getenv("USE_MCP", "false").lower() == "true"
MCP_PW_SERVER_URL = os.getenv("MCP_PW_SERVER_URL", "http://localhost:8765")
MCP_PW_TIMEOUT_MS = int(os.getenv("MCP_PW_TIMEOUT_MS", "5000"))
MCP_PW_API_KEY = os.getenv("MCP_PW_API_KEY")


class MCPPlaywrightClient:
    """
    Async client for MCP Playwright server.

    Provides step-scoped discovery, gates, healing, and diagnostics
    with automatic fallback when server unavailable.
    """

    def __init__(self):
        self.base_url = MCP_PW_SERVER_URL
        self.timeout = aiohttp.ClientTimeout(total=MCP_PW_TIMEOUT_MS / 1000)
        self.headers = {}
        if MCP_PW_API_KEY:
            self.headers["Authorization"] = f"Bearer {MCP_PW_API_KEY}"

        self._available = None  # Cache availability check
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers
            )
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def is_available(self) -> bool:
        """
        Check if MCP Playwright server is available.

        Returns:
            True if server responds to health check, False otherwise
        """
        if not USE_MCP:
            return False

        if self._available is not None:
            return self._available

        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health") as resp:
                if resp.status == 200:
                    self._available = True
                    logger.info(f"MCP Playwright server available at {self.base_url}")
                    return True
        except Exception as e:
            logger.debug(f"MCP Playwright server unavailable: {e}")

        self._available = False
        return False

    async def discover_locator(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Discover locator for a step using MCP Playwright.

        Args:
            step: Step dict with keys: target, action, value, etc.

        Returns:
            {
                "selector": str,
                "strategy": str,  # e.g., "role", "label", "testId", "css"
                "confidence": float,  # 0.0-1.0
                "notes": str  # Additional context
            }
            or None if not found/unavailable
        """
        if not await self.is_available():
            return None

        try:
            target = step.get("target") or step.get("element") or ""
            action = step.get("action", "click")
            value = step.get("value", "")

            payload = {
                "target": target,
                "action": action,
                "value": value,
                "hints": step.get("hints", {})
            }

            session = await self._get_session()
            async with session.post(f"{self.base_url}/discover", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"MCP discovered selector for '{target}': {result.get('selector')} (strategy: {result.get('strategy')})")
                    return result
                else:
                    logger.warning(f"MCP discover failed with status {resp.status}")
                    return None

        except Exception as e:
            logger.error(f"MCP discover_locator error: {e}", exc_info=True)
            return None

    async def assert_actionable(self, selector: str, action: str) -> Optional[Dict[str, Any]]:
        """
        Assert that selector is actionable for given action.

        Args:
            selector: CSS selector or other locator string
            action: Action type (click, fill, etc.)

        Returns:
            {
                "unique": bool,
                "visible": bool,
                "enabled": bool,
                "stable_bbox": bool,
                "reasons": List[str]  # Failure reasons if any
            }
            or None if unavailable
        """
        if not await self.is_available():
            return None

        try:
            payload = {
                "selector": selector,
                "action": action
            }

            session = await self._get_session()
            async with session.post(f"{self.base_url}/assert_actionable", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.debug(f"MCP actionable gates for '{selector}': {result}")
                    return result
                else:
                    logger.warning(f"MCP assert_actionable failed with status {resp.status}")
                    return None

        except Exception as e:
            logger.error(f"MCP assert_actionable error: {e}", exc_info=True)
            return None

    async def reveal(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute reveal actions to make element accessible.

        Actions may include:
        - Scroll element into view
        - Dismiss overlays/modals
        - Wait for network idle
        - Bring frame to front

        Args:
            step: Step dict with target information

        Returns:
            {
                "actions": List[str],  # Actions performed
                "success": bool,
                "notes": str
            }
            or None if unavailable
        """
        if not await self.is_available():
            return None

        try:
            target = step.get("target") or step.get("element") or ""
            selector = step.get("selector", "")

            payload = {
                "target": target,
                "selector": selector
            }

            session = await self._get_session()
            async with session.post(f"{self.base_url}/reveal", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"MCP reveal actions for '{target}': {result.get('actions', [])}")
                    return result
                else:
                    logger.warning(f"MCP reveal failed with status {resp.status}")
                    return None

        except Exception as e:
            logger.error(f"MCP reveal error: {e}", exc_info=True)
            return None

    async def reprobe(self, target: str, heal_round: int) -> Optional[Dict[str, Any]]:
        """
        Reprobe for element with relaxed strategies.

        Fallback chain: role → label → testId → css

        Args:
            target: Target element description
            heal_round: Current healing round number

        Returns:
            {
                "selector": str,
                "fallback_chain": List[str],  # Strategies attempted
                "strategy": str,  # Strategy that succeeded
                "confidence": float
            }
            or None if not found/unavailable
        """
        if not await self.is_available():
            return None

        try:
            payload = {
                "target": target,
                "heal_round": heal_round
            }

            session = await self._get_session()
            async with session.post(f"{self.base_url}/reprobe", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"MCP reprobe for '{target}' (round {heal_round}): {result.get('selector')} via {result.get('strategy')}")
                    return result
                else:
                    logger.warning(f"MCP reprobe failed with status {resp.status}")
                    return None

        except Exception as e:
            logger.error(f"MCP reprobe error: {e}", exc_info=True)
            return None

    async def debug_probe(self, selector: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed diagnostic information about a selector.

        Args:
            selector: Selector to probe

        Returns:
            {
                "visibility": Dict,  # visible, opacity, display, etc.
                "bbox": Dict,  # x, y, width, height
                "aria": Dict,  # role, label, description
                "frame": str,  # Frame context
                "tree": str  # DOM tree snippet
            }
            or None if unavailable
        """
        if not await self.is_available():
            return None

        try:
            payload = {
                "selector": selector
            }

            session = await self._get_session()
            async with session.post(f"{self.base_url}/debug_probe", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.debug(f"MCP debug probe for '{selector}': {result}")
                    return result
                else:
                    logger.warning(f"MCP debug_probe failed with status {resp.status}")
                    return None

        except Exception as e:
            logger.error(f"MCP debug_probe error: {e}", exc_info=True)
            return None

    async def suggest_locator(self, target: str) -> Optional[Dict[str, Any]]:
        """
        Get Playwright Test recorder-style locator suggestion.

        Args:
            target: Target element description

        Returns:
            {
                "locator": str,  # PW Test locator (e.g., page.getByRole('button', { name: 'Login' }))
                "line": str,  # Code line for generator
                "confidence": float
            }
            or None if unavailable
        """
        if not await self.is_available():
            return None

        try:
            payload = {
                "target": target
            }

            session = await self._get_session()
            async with session.post(f"{self.base_url}/suggest_locator", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.debug(f"MCP suggest locator for '{target}': {result.get('locator')}")
                    return result
                else:
                    logger.warning(f"MCP suggest_locator failed with status {resp.status}")
                    return None

        except Exception as e:
            logger.error(f"MCP suggest_locator error: {e}", exc_info=True)
            return None


# Singleton instance
_client: Optional[MCPPlaywrightClient] = None


@lru_cache(maxsize=1)
def get_client() -> MCPPlaywrightClient:
    """
    Get singleton MCP Playwright client instance.

    Returns:
        MCPPlaywrightClient instance
    """
    global _client
    if _client is None:
        _client = MCPPlaywrightClient()
    return _client


async def cleanup_client():
    """Close the MCP client session."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
