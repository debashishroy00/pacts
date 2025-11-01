"""
MCP Discovery Adapter with CDP Integration
============================================

Read-only discovery via MCP Playwright + CDP (attached to SAME Playwright browser).
Provides region-scoped accessibility queries and ancestor enrichment for Salesforce Lightning.

Key Features:
- AX tree queries scoped to regions (e.g., "App Launcher" dialog)
- CDP ancestor enrichment (data-aura-class, Lightning component IDs)
- Actionability verification (read-only checks)
- Robust selector resolution (role+name preferred, Lightning-aware fallback)

Usage:
    mcp_disc = MCPDiscovery(mcp_client, cdp_client)
    cand = await mcp_disc.discover_accounts_within_launcher()
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MCPDiscovery:
    """
    Read-only discovery via MCP Playwright + CDP (attached to SAME Playwright browser).
    Assumes a single long-lived MCP client per run.
    """

    def __init__(self, mcp_client, cdp_client):
        """
        Initialize MCP discovery adapter.

        Args:
            mcp_client: MCP Playwright JSON-RPC client (list_tools, call_tool)
            cdp_client: Chrome DevTools Protocol client (call method)
        """
        self.mcp = mcp_client  # JSON-RPC: list_tools(), call_tool(name, args)
        self.cdp = cdp_client  # JSON-RPC: call(method, params)

    async def ax_query(
        self,
        role: Optional[str],
        name_regex: Optional[str],
        within_region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query the accessibility tree. Returns candidate dicts with meta: {role,name,region,axNodeId}.

        Args:
            role: ARIA role to filter by (e.g., "button", "link")
            name_regex: Regex pattern for accessible name
            within_region: Optional region name to scope query (e.g., "App Launcher")

        Returns:
            List of candidate dictionaries with AX metadata
        """
        args = {"role": role, "name_regex": name_regex}

        try:
            # MCP tool call for AX query
            nodes = await self.mcp.call_tool("query_accessibility", args)
        except Exception as e:
            logger.warning(f"[MCP-AX] query_accessibility failed: {e}")
            return []

        cands = []
        for n in nodes or []:
            region = await self._region_of(n)

            # Filter by region if specified
            if within_region is None or (
                region and within_region.lower() in region.lower()
            ):
                cands.append(
                    {
                        "selector": None,  # resolved later
                        "score": 0.0,
                        "meta": {
                            "axRole": n.get("role"),
                            "axName": n.get("name"),
                            "region": region,
                            "axNodeId": n.get("nodeId"),
                            "backendDOMNodeId": n.get("backendDOMNodeId"),
                        },
                    }
                )

        logger.info(
            f"[MCP-AX] Query: role={role} name={name_regex} region={within_region} → {len(cands)} candidates"
        )
        return cands

    async def enrich_with_ancestors(self, cand: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decorate candidate with ancestor roles and attributes via CDP DOMSnapshot + AX.

        Args:
            cand: Candidate dictionary with backendDOMNodeId

        Returns:
            Enriched candidate with ancestor_attrs and ancestor_roles
        """
        backend_id = cand["meta"].get("backendDOMNodeId")
        if not backend_id:
            return cand

        # Pull attributes up the ancestor chain using CDP
        attrs_chain, roles_chain = await self._ancestor_attributes_and_roles(
            backend_id
        )
        cand["meta"]["ancestor_attrs"] = attrs_chain
        cand["meta"]["ancestor_roles"] = roles_chain

        logger.debug(
            f"[MCP-CDP] Enriched candidate: aura_class={attrs_chain.get('data-aura-class', 'N/A')}"
        )
        return cand

    async def assert_actionable(self, cand: Dict[str, Any]) -> bool:
        """
        Ask MCP to confirm actionability (visible, enabled, stable). Read-only check.

        Args:
            cand: Candidate dictionary

        Returns:
            True if element is actionable, False otherwise
        """
        try:
            backend_id = cand["meta"].get("backendDOMNodeId")
            ok = await self.mcp.call_tool(
                "assert_actionable", {"backendDOMNodeId": backend_id}
            )
            return bool(ok)
        except Exception as e:
            logger.warning(f"[MCP] assert_actionable failed: {e}")
            return False

    async def resolve_selector(self, cand: Dict[str, Any]) -> Optional[str]:
        """
        Convert accessibility/CDP reference to a stable selector when possible.
        Prefers role+name; falls back to CSS with Lightning anchors.

        Args:
            cand: Enriched candidate dictionary

        Returns:
            Playwright selector string or None
        """
        role = cand["meta"].get("axRole")
        name = cand["meta"].get("axName")

        # Prefer robust role selector
        if role and name:
            # Escape special characters in name
            escaped_name = name.replace('"', '\\"')
            return f'role={role}[name="{escaped_name}"]'

        # Lightning-friendly fallback using data-* ancestry as anchors (best-effort)
        aura = cand["meta"].get("ancestor_attrs", {}).get("data-aura-class", "")
        if "appLauncher" in aura or "al-menu" in aura:
            return 'role=button[name="Accounts"]'

        return None

    async def discover_accounts_within_launcher(self) -> Optional[Dict[str, Any]]:
        """
        Salesforce-specific: Discover "Accounts" button within App Launcher region.

        Uses region-scoped AX query + Lightning ancestor scoring.

        Returns:
            Best candidate with selector or fallback instruction
        """
        # 1) AX query for Accounts buttons scoped to region "App Launcher"
        cands = await self.ax_query(
            role="button", name_regex="^Accounts$", within_region="App Launcher"
        )

        if not cands:
            logger.warning(
                "[MCP-SF] No Accounts candidates found in App Launcher region"
            )
            return {"fallback": "launcher_search"}

        # 2) Enrich + Lightning rank
        ranked = []
        for c in cands:
            c = await self.enrich_with_ancestors(c)
            score = 0

            # Lightning-specific scoring
            aura = c["meta"].get("ancestor_attrs", {}).get("data-aura-class", "")
            if "appLauncher" in aura or "al-menu" in aura:
                score += 2

            roles = c["meta"].get("ancestor_roles", [])
            if any(r in ("menu", "grid", "dialog") for r in roles):
                score += 1

            c["score"] = score
            ranked.append(c)

        # Pick highest score
        best = max(ranked, key=lambda x: x["score"])

        logger.info(
            f"[MCP-SF] Picked Accounts candidate: score={best['score']} region={best['meta'].get('region')}"
        )

        # 3) Actionability check (read-only)
        if not await self.assert_actionable(best):
            logger.warning(
                "[MCP-SF] Best candidate not actionable, using fallback search"
            )
            return {"fallback": "launcher_search"}

        # 4) Resolve to a selector PACTS can act on locally
        best["selector"] = await self.resolve_selector(best) or 'role=button[name="Accounts"]'

        return best

    # ---------- Internals ----------

    async def _region_of(self, ax_node: Dict[str, Any]) -> Optional[str]:
        """
        Walk up AX ancestors (from MCP) until a region/dialog with a name is found.

        Args:
            ax_node: Accessibility node dictionary

        Returns:
            Region name or None
        """
        try:
            region = await self.mcp.call_tool(
                "find_region_ancestor", {"nodeId": ax_node.get("nodeId")}
            )
            # returns {"role":"dialog","name":"App Launcher"} or None
            if region and region.get("name"):
                return region["name"]
        except Exception as e:
            logger.debug(f"[MCP-AX] find_region_ancestor failed: {e}")

        return None

    async def _ancestor_attributes_and_roles(
        self, backend_id: int
    ) -> Tuple[Dict[str, str], List[str]]:
        """
        Use CDP to walk the DOM ancestors and collect interesting attributes/roles.

        Args:
            backend_id: Backend DOM node ID from AX tree

        Returns:
            (flattened_attrs, roles_chain) tuple
        """
        attrs: Dict[str, str] = {}
        roles: List[str] = []

        try:
            # Get node + ancestors via CDP
            node_desc = await self.cdp.call(
                "DOM.describeNode",
                {"backendNodeId": backend_id, "depth": -1, "pierce": True},
            )

            chain = self._collect_ancestors_chain(node_desc)

            # Extract attributes from each ancestor
            for ancestor in chain:
                if "attributes" in ancestor:
                    # Attributes come as flat list: [k1, v1, k2, v2, ...]
                    kv = dict(
                        zip(ancestor["attributes"][::2], ancestor["attributes"][1::2])
                    )

                    # Keep Lightning-relevant attributes
                    for key in (
                        "data-aura-class",
                        "data-componentid",
                        "class",
                        "role",
                        "aria-label",
                    ):
                        if key in kv and key not in attrs:
                            attrs[key] = kv[key]

                    # Collect role if present
                    if "role" in kv:
                        roles.append(kv["role"])

        except Exception as e:
            logger.debug(f"[MCP-CDP] Ancestor enrichment failed: {e}")

        return attrs, roles

    def _collect_ancestors_chain(
        self, describe_node_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Flatten current node + ancestors from CDP describeNode result.

        Args:
            describe_node_result: Result from DOM.describeNode CDP call

        Returns:
            List of ancestor node dictionaries
        """
        nodes: List[Dict[str, Any]] = []
        cur = describe_node_result.get("node", {})

        while cur:
            nodes.append(cur)
            # Walk up: parent, shadowHost, or stop
            cur = cur.get("parent") or cur.get("shadowHost") or None

        return nodes


# ========== Launcher Search Fallback ==========


async def launcher_search_accounts(page):
    """
    Robust fallback: Use App Launcher search to navigate to Accounts.

    Works across all Salesforce Lightning editions without site-specific selectors.

    Args:
        page: Playwright Page object
    """
    logger.info("[FALLBACK] Using App Launcher search for Accounts")

    try:
        # Find App Launcher dialog
        panel = page.get_by_role("dialog", name=/App Launcher/i)

        # Use search combobox
        search = panel.get_by_role("combobox", name=/Search apps and items/i)
        await search.fill("Accounts")
        await page.keyboard.press("Enter")

        # Click the Accounts result
        await panel.get_by_role("button", name=/^Accounts$/i).first.click()

        logger.info("[FALLBACK] Launcher search succeeded")

    except Exception as e:
        logger.error(f"[FALLBACK] Launcher search failed: {e}")
        raise
