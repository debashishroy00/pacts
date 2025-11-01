"""
MCP Client - Model Context Protocol interface to MCP Playwright servers.

This client connects to MCP Playwright servers using the official MCP SDK
with stdio transport (subprocess communication).

Two server types:
1. MCP Playwright - Browser control (navigate, click, fill, query, assert)
2. MCP Playwright Test - Codegen (generate test files)
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Environment configuration
USE_MCP = os.getenv("USE_MCP", "false").lower() == "true"
MCP_TIMEOUT_MS = int(os.getenv("MCP_TIMEOUT_MS", "30000"))


class MCPClient:
    """
    Stdio-based MCP client for Playwright servers.

    Handles tool discovery, method calls, and response parsing via subprocess.
    """

    def __init__(self, server_args: List[str], name: str = "mcp", port: Optional[int] = None):
        self.server_args = server_args
        self.name = name
        self.port = port
        self._session: Optional[ClientSession] = None
        self._read = None
        self._write = None
        self._stdio_context = None
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._tool_map: Dict[str, str] = {}  # name -> actual_tool_name
        self._initialized = False

    async def initialize(self):
        """Initialize the MCP connection via stdio."""
        if self._initialized:
            return

        try:
            # Build server parameters
            args = ["-y"] + self.server_args
            if self.port:
                args.extend(["--port", str(self.port)])
            args.append("--headless")
            # Enable vision capability for XY coordinate fallback
            args.extend(["--caps", "vision"])

            server_params = StdioServerParameters(
                command="npx",
                args=args,
                env=None
            )

            logger.info(f"[{self.name}] Starting MCP server: npx {' '.join(args)}")

            # Start the stdio client
            self._stdio_context = stdio_client(server_params)
            self._read, self._write = await self._stdio_context.__aenter__()

            # Create session
            self._session = ClientSession(self._read, self._write)
            await self._session.__aenter__()

            # Initialize the session
            await self._session.initialize()

            self._initialized = True
            logger.info(f"[{self.name}] MCP connection initialized")

        except Exception as e:
            logger.error(f"[{self.name}] Failed to initialize MCP: {e}")
            raise

    async def close(self):
        """Close the MCP session and stdio connection."""
        if not self._initialized:
            return

        try:
            if self._session:
                try:
                    await self._session.__aexit__(None, None, None)
                except (RuntimeError, Exception) as e:
                    logger.debug(f"[{self.name}] Session close: {e}")
                self._session = None

            if self._stdio_context:
                try:
                    await self._stdio_context.__aexit__(None, None, None)
                except (RuntimeError, Exception) as e:
                    logger.debug(f"[{self.name}] Stdio close: {e}")
                self._stdio_context = None

        finally:
            self._initialized = False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.

        Returns:
            List of tool definitions with name, description, parameters
        """
        if not self._initialized:
            await self.initialize()

        if self._tools_cache is not None:
            return self._tools_cache

        try:
            result = await self._session.list_tools()

            if result and hasattr(result, 'tools'):
                self._tools_cache = [
                    {
                        "name": tool.name,
                        "description": tool.description if hasattr(tool, 'description') else "",
                        "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    }
                    for tool in result.tools
                ]

                # Build tool name map
                for tool in self._tools_cache:
                    name = tool.get("name", "")
                    self._tool_map[name] = name

                logger.info(f"[{self.name}] Discovered {len(self._tools_cache)} tools: {list(self._tool_map.keys())}")
                return self._tools_cache

        except Exception as e:
            logger.error(f"[{self.name}] Failed to list tools: {e}")

        logger.warning(f"[{self.name}] No tools discovered")
        return []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result or None if failed
        """
        if not self._initialized:
            await self.initialize()

        import time
        start_ms = int(time.time() * 1000)

        try:
            result = await self._session.call_tool(tool_name, arguments)

            elapsed_ms = int(time.time() * 1000) - start_ms

            logger.info(f"[{self.name}] MCP_CALL name={tool_name} ms={elapsed_ms} ok=True")

            # Extract content from result
            if result and hasattr(result, 'content'):
                return {"content": result.content}

            return {"result": str(result)}

        except Exception as e:
            elapsed_ms = int(time.time() * 1000) - start_ms
            logger.error(f"[{self.name}] MCP_CALL name={tool_name} ms={elapsed_ms} ok=False error={e}")
            return None

    async def is_available(self) -> bool:
        """Check if MCP server is available."""
        if not USE_MCP:
            return False

        try:
            tools = await self.list_tools()
            return len(tools) > 0
        except Exception:
            return False


# Singleton instances
_playwright_client: Optional[MCPClient] = None
_playwright_test_client: Optional[MCPClient] = None


def get_playwright_client() -> MCPClient:
    """Get singleton MCP Playwright client (browser control)."""
    global _playwright_client
    if _playwright_client is None:
        # Use @playwright/mcp for browser control
        _playwright_client = MCPClient(
            server_args=["@playwright/mcp@latest"],
            name="MCP_PW",
            port=None  # Let MCP choose port
        )
    return _playwright_client


def get_playwright_test_client() -> MCPClient:
    """Get singleton MCP Playwright Test client (codegen)."""
    global _playwright_test_client
    if _playwright_test_client is None:
        # Use @playwright/mcp for test generation (same package, different usage)
        _playwright_test_client = MCPClient(
            server_args=["@playwright/mcp@latest"],
            name="MCP_PW_TEST",
            port=None
        )
    return _playwright_test_client


async def cleanup_clients():
    """Close all MCP client sessions."""
    global _playwright_client, _playwright_test_client

    if _playwright_client:
        await _playwright_client.close()
        _playwright_client = None

    if _playwright_test_client:
        await _playwright_test_client.close()
        _playwright_test_client = None


# ==========================================
# PACTS Integration Helpers
# ==========================================

async def discover_locator_via_mcp(intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Use MCP Playwright to discover a locator for a PACTS intent.

    Uses MCP browser_snapshot to get accessibility tree, then searches for
    matching elements using fuzzy text matching.

    Args:
        intent: PACTS intent dict with element, action, value

    Returns:
        Dict with selector, confidence, strategy, or None if not found
    """
    if not USE_MCP:
        return None

    target = (intent.get("element") or intent.get("target") or intent.get("intent") or "").strip()
    action = (intent.get("action") or "").lower()

    if not target:
        return None

    try:
        client = get_playwright_client()

        # Use browser_snapshot to get accessibility tree
        result = await client.call_tool("browser_snapshot", {})

        if not result or not result.get("content"):
            logger.warning(f"[MCP] No snapshot content received")
            return None

        # Extract text content from snapshot
        snapshot_content = result.get("content", [])

        # Parse snapshot to find matching elements
        # Snapshot contains TextContent objects or dicts with 'text' attribute
        snapshot_text = ""
        for item in snapshot_content:
            # Handle TextContent objects (they have a .text attribute)
            if hasattr(item, 'text'):
                snapshot_text += item.text + "\n"
            # Handle dict format
            elif isinstance(item, dict):
                snapshot_text += item.get("text", "") + "\n"
            # Handle plain strings
            elif isinstance(item, str):
                snapshot_text += item + "\n"

        # Normalize target for matching
        target_lower = target.lower().strip()

        # Check if target appears in accessibility tree
        if target_lower in snapshot_text.lower():
            logger.info(f"[MCP] Found '{target}' in accessibility tree")

            # For now, return a result indicating we found it in the tree
            # The actual selector discovery will still use local strategies
            # This serves as a confidence booster
            return {
                "selector": None,  # Let local strategies find the actual selector
                "score": 0.80,
                "meta": {
                    "strategy": "mcp_snapshot_confirmed",
                    "channel": "mcp",
                    "notes": f"Element '{target}' confirmed in accessibility tree"
                }
            }

        logger.debug(f"[MCP] Target '{target}' not found in accessibility tree")
        return None

    except Exception as e:
        logger.error(f"[MCP] Discovery failed: {e}")
        return None


async def discover_and_act_via_mcp(intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Use MCP to discover AND execute action directly (Phase 1 implementation).

    This bypasses Playwright selector discovery entirely and uses MCP's
    accessibility tree traversal to find and interact with elements.

    Handles Shadow DOM, React components, and complex SPAs automatically.

    Args:
        intent: PACTS intent dict with element, action, value

    Returns:
        Dict with special MCP_* selector indicating action was performed,
        or None if MCP couldn't handle it
    """
    if not USE_MCP:
        return None

    target = (intent.get("element") or intent.get("target") or "").strip()
    action = (intent.get("action") or "").lower()
    value = intent.get("value")

    if not target or not action:
        return None

    try:
        client = get_playwright_client()

        # Determine best ref type based on context
        # Priority: text > role > placeholder > label
        ref_type = "text"  # Most universal

        # Try to execute action directly via MCP
        result = None
        tool_name = None

        if action == "click":
            tool_name = "browser_click"
            result = await client.call_tool("browser_click", {
                "element": target,
                "ref": ref_type
            })

        elif action == "fill":
            tool_name = "browser_type"
            result = await client.call_tool("browser_type", {
                "element": target,
                "ref": ref_type,
                "text": value or "",
                "submit": False
            })

        elif action == "press":
            # For press actions, try typing first, then use keyboard
            if value and value.lower() == "enter":
                tool_name = "browser_press_key"
                result = await client.call_tool("browser_press_key", {
                    "key": "Enter"
                })
            else:
                tool_name = "browser_type"
                result = await client.call_tool("browser_type", {
                    "element": target,
                    "ref": ref_type,
                    "text": value or "",
                    "submit": True if value and value.lower() == "enter" else False
                })

        elif action == "select":
            tool_name = "browser_select_option"
            result = await client.call_tool("browser_select_option", {
                "element": target,
                "ref": ref_type,
                "values": [value] if value else []
            })

        elif action == "hover":
            tool_name = "browser_hover"
            result = await client.call_tool("browser_hover", {
                "element": target,
                "ref": ref_type
            })

        # Check if MCP successfully performed the action
        if result:
            # MCP tools return result with content array
            # Success if no error in response
            has_error = False
            if isinstance(result, dict):
                if result.get("error"):
                    has_error = True
                    logger.warning(f"[MCP] Action failed: {result.get('error')}")
                elif result.get("content"):
                    # Check content for error messages
                    content = result.get("content", [])
                    for item in content:
                        if isinstance(item, dict):
                            text = item.get("text", "")
                            if "error" in text.lower() or "failed" in text.lower():
                                has_error = True
                                break

            if not has_error:
                logger.info(f"[MCP] Successfully performed {action} on '{target}' using {tool_name}")

                # Return special selector indicating MCP already performed the action
                return {
                    "selector": f"MCP_{action.upper()}:{target}",
                    "score": 0.95,
                    "meta": {
                        "strategy": "mcp_direct_action",
                        "tool": tool_name,
                        "element": target,
                        "action": action,
                        "ref_type": ref_type,
                        "action_completed": True  # Critical flag for executor
                    }
                }

        logger.debug(f"[MCP] Could not perform {action} on '{target}' - no error but no success confirmation")
        return None

    except Exception as e:
        logger.warning(f"[MCP] Action tool failed: {e}")
        return None


async def execute_action_via_mcp(action: str, selector: str, value: Optional[str] = None) -> bool:
    """
    Execute an action via MCP Playwright.

    Args:
        action: Action type (click, fill, press, select, etc.)
        selector: CSS selector or locator
        value: Optional value for fill/select actions

    Returns:
        True if successful, False otherwise
    """
    if not USE_MCP:
        return False

    try:
        client = get_playwright_client()

        if action == "click":
            result = await client.call_tool("browser_click", {"selector": selector})
        elif action == "fill":
            result = await client.call_tool("browser_type", {
                "selector": selector,
                "text": value or ""
            })
        elif action == "press":
            # Use browser_press_key for keyboard actions
            result = await client.call_tool("browser_press_key", {"key": value or "Enter"})
        elif action == "select":
            result = await client.call_tool("browser_select_option", {
                "selector": selector,
                "value": value or ""
            })
        else:
            logger.warning(f"[MCP] Unknown action: {action}")
            return False

        return result is not None

    except Exception as e:
        logger.error(f"[MCP] Action failed: {e}")
        return False
