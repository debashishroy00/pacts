"""
PACTS Production CLI - Zero-Code Test Execution

Users can run tests with a simple command:
    pacts test --req REQ-001
    pacts test --req REQ-LOGIN-001 --headed
    pacts test --req REQ-SHOPPING-001 --slow-mo 500

The CLI automatically:
- Discovers requirement files (Excel or JSON)
- Parses test specifications
- Executes the full agent pipeline
- Displays results in a user-friendly format
"""

from __future__ import annotations
import sys
import asyncio
import json
import os
from pathlib import Path
from typing import Optional
import click

from ..graph.state import RunState
from ..graph.build_graph import ainvoke_graph
from ..storage.init import get_storage, shutdown_storage


# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print section header."""
    print()
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print()


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


async def _run_pipeline_with_storage(state: RunState) -> RunState:
    """
    Run pipeline with storage initialization and cleanup.

    Args:
        state: Initial run state

    Returns:
        Final run state after execution
    """
    storage = None

    try:
        # Initialize storage if memory is enabled
        if os.getenv("ENABLE_MEMORY", "true").lower() == "true":
            print("[STORAGE] Initializing memory & persistence...")
            storage = await get_storage()

            if storage:
                health = await storage.healthcheck()
                if health.get("healthy"):
                    print(f"{Colors.GREEN}✓ Memory system ready{Colors.END}")
                    if os.getenv("CACHE_DEBUG", "false").lower() == "true":
                        print("[STORAGE] Cache debug mode enabled")
                else:
                    print(f"{Colors.YELLOW}⚠ Memory system degraded, continuing without cache{Colors.END}")

        # Run the actual pipeline
        result = await ainvoke_graph(state)

        return result

    finally:
        # Cleanup storage on exit
        if storage:
            await shutdown_storage()


def _check_mcp_status(mcp_enabled: bool) -> dict:
    """
    Check MCP Playwright server availability with 3-probe gate.

    Phase A (Discovery-Only): MCP enriches discovery; all actions executed locally.

    3-Probe Gate:
    - Probe A: Check USE_MCP environment variable
    - Probe B: Ping MCP server (list_tools must return expected tools)
    - Probe C: Verify NOT in actions mode (actions disabled by default)

    Returns:
        dict with keys:
            - enabled: bool (USE_MCP=true)
            - available: bool (MCP server is accessible and responding)
            - attached: bool (MCP attached to same browser - always False in Phase A)
            - mode: str ("discovery-only" or "actions")
            - error: str or None
            - fallback: bool (will fall back to local strategies)
            - message: str (status description)
    """
    import os

    # Probe A: Check USE_MCP env variable
    use_mcp = os.getenv("USE_MCP", "false").lower() == "true"

    if not use_mcp and not mcp_enabled:
        return {
            "enabled": False,
            "available": False,
            "attached": False,
            "mode": "disabled",
            "error": None,
            "fallback": True,
            "message": "MCP disabled (USE_MCP=false)"
        }

    # MCP requested but env var not set
    if not use_mcp and mcp_enabled:
        return {
            "enabled": False,
            "available": False,
            "attached": False,
            "mode": "disabled",
            "error": "USE_MCP environment variable not set",
            "fallback": True,
            "message": "MCP requested via --mcp but USE_MCP=false in .env"
        }

    # Probe B: Try to list tools from MCP server
    try:
        from ..mcp.mcp_client import get_playwright_client

        try:
            client = get_playwright_client()

            # Actually test if MCP server responds
            # This will initialize the client and list tools
            import asyncio
            tools = asyncio.run(client.list_tools())

            # Verify we got expected Playwright tools
            if not tools or len(tools) == 0:
                return {
                    "enabled": True,
                    "available": False,
                    "attached": False,
                    "mode": "discovery-only",
                    "error": "MCP server returned no tools",
                    "fallback": True,
                    "message": "MCP server accessible but no tools available"
                }

            # Check for expected tool names
            tool_names = [t.get("name", "") for t in tools]
            has_browser_tools = any(
                name.startswith("browser_") for name in tool_names
            )

            if not has_browser_tools:
                return {
                    "enabled": True,
                    "available": False,
                    "attached": False,
                    "mode": "discovery-only",
                    "error": "Missing expected browser tools",
                    "fallback": True,
                    "message": f"MCP returned {len(tools)} tools but no browser_* tools found"
                }

            # Probe C: Check if actions mode is enabled (should be False for Phase A)
            mcp_actions_enabled = os.getenv("MCP_ACTIONS_ENABLED", "false").lower() == "true"
            mcp_attach_ws = os.getenv("MCP_ATTACH_WS", "false").lower() == "true"

            # Phase A: Actions should be disabled
            if mcp_actions_enabled and not mcp_attach_ws:
                return {
                    "enabled": True,
                    "available": False,
                    "attached": False,
                    "mode": "invalid",
                    "error": "MCP_ACTIONS_ENABLED=true but MCP_ATTACH_WS=false",
                    "fallback": True,
                    "message": "Cannot enable MCP actions without browser attach (wsEndpoint required)"
                }

            # Success: MCP available in discovery-only mode
            mode = "actions" if mcp_actions_enabled else "discovery-only"
            return {
                "enabled": True,
                "available": True,
                "attached": mcp_attach_ws,
                "mode": mode,
                "error": None,
                "fallback": False,
                "message": f"MCP Playwright connected ({mode}, {len(tools)} tools)"
            }

        except Exception as e:
            return {
                "enabled": True,
                "available": False,
                "attached": False,
                "mode": "discovery-only",
                "error": str(e),
                "fallback": True,
                "message": f"MCP server not accessible: {str(e)[:100]}"
            }

    except ImportError as e:
        return {
            "enabled": True,
            "available": False,
            "error": str(e),
            "fallback": True,
            "message": "MCP client not installed"
        }


def _display_mcp_status(status: dict):
    """
    Display MCP Playwright status to user.

    Args:
        status: Status dict from _check_mcp_status
    """
    print()
    print(f"{Colors.BOLD}Discovery Engine Status:{Colors.END}")

    if not status["enabled"]:
        # MCP disabled - show local heuristics
        print_info("MCP Playwright: DISABLED")
        print(f"  → Using local heuristics (label, placeholder, role_name)")
        print(f"  → Accuracy: ~85-90% for standard web apps")
        print(f"  → Tip: Set USE_MCP=true in .env for MCP discovery")

    elif status["available"]:
        # MCP enabled and connected - show mode
        mode = status.get("mode", "unknown")
        attached = status.get("attached", False)

        if mode == "discovery-only":
            print_success("MCP Playwright: CONNECTED (discovery-only)")
            print(f"  → MCP enriches discovery, actions executed locally")
            print(f"  → Shadow DOM, frames, and ARIA fully supported")
            print(f"  → Expected accuracy: 95%+ across all element types")
        elif mode == "actions" and attached:
            print_success("MCP Playwright: CONNECTED (actions enabled, attached)")
            print(f"  → MCP performs discovery AND actions")
            print(f"  → Attached to same browser (wsEndpoint)")
            print(f"  → Full production mode")
        elif mode == "actions" and not attached:
            print_warning("MCP Playwright: INVALID CONFIG")
            print(f"  → Actions enabled but not attached to browser")
            print(f"  → Set PLAYWRIGHT_WS_ENDPOINT or disable MCP_ACTIONS_ENABLED")
        else:
            print_success(f"MCP Playwright: CONNECTED ({mode})")
            print(f"  → {status.get('message', 'Ready')}")

    else:
        # MCP enabled but unavailable - show fallback
        print_warning("MCP Playwright: UNAVAILABLE")
        print(f"  → Reason: {status['message']}")
        print(f"  → Falling back to local heuristics (85-90% accuracy)")
        print()
        print(f"  To enable MCP Playwright:")
        print(f"    1. Start MCP server: npx @modelcontextprotocol/server-playwright")
        print(f"    2. Set USE_MCP=true in .env")
        print(f"    3. Verify connection with health check")

    print()


def discover_requirement_file(req_id: str) -> Optional[Path]:
    """
    Discover requirement file by REQ-ID.

    Searches in order:
    1. requirements/{req_id}.txt (natural language)
    2. requirements/{req_id}.xlsx
    3. requirements/{req_id}.json
    4. specs/{req_id}.json
    5. specs/{req_id}.xlsx

    Args:
        req_id: Requirement ID (e.g., REQ-001) or file name pattern

    Returns:
        Path to file if found, None otherwise
    """
    search_paths = [
        Path("requirements") / f"{req_id}.txt",  # Natural language (NEW)
        Path("requirements") / f"{req_id}.xlsx",
        Path("requirements") / f"{req_id}.json",
        Path("specs") / f"{req_id}.json",
        Path("specs") / f"{req_id}.xlsx",
        # Also try lowercase versions
        Path("specs") / f"{req_id.lower()}.json",
        Path("requirements") / f"{req_id.lower()}.txt",
        # Try pattern matching (e.g., saucedemo_login.json for REQ-LOGIN-001)
    ]

    # Also search for partial matches in specs/
    specs_dir = Path("specs")
    if specs_dir.exists():
        for file in specs_dir.glob("*.json"):
            # Check if req_id appears in filename
            if req_id.lower() in file.stem.lower():
                return file

            # Check if req_id matches inside JSON file
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if content.get('req_id') == req_id:
                        return file
            except:
                pass

    for path in search_paths:
        if path.exists():
            return path

    return None


def parse_json_file(file_path: Path) -> dict:
    """Parse JSON requirement file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_natural_language_file(file_path: Path) -> dict:
    """
    Parse natural language requirement file (.txt).

    This returns a special marker dict that tells the Planner to use LLM parsing.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        text_content = f.read()

    return {
        "_natural_language": True,
        "natural_language_text": text_content,
        "source_file": str(file_path)
    }


def parse_excel_file(file_path: Path) -> dict:
    """
    Parse Excel requirement file.

    TODO: Implement Excel parsing with openpyxl
    For now, raises NotImplementedError with helpful message.
    """
    raise NotImplementedError(
        f"Excel parsing not yet implemented.\n"
        f"Please convert {file_path.name} to JSON format.\n"
        f"See specs/saucedemo_login.json for example format."
    )


def load_requirement_spec(req_id: str) -> tuple[dict, Path]:
    """
    Load requirement specification from file.

    Args:
        req_id: Requirement ID

    Returns:
        Tuple of (spec dict, file path)

    Raises:
        FileNotFoundError: If requirement file not found
        NotImplementedError: If Excel parsing not yet available
    """
    # Discover file
    file_path = discover_requirement_file(req_id)

    if not file_path:
        raise FileNotFoundError(
            f"Requirement '{req_id}' not found.\n"
            f"Searched in: requirements/ and specs/ directories.\n"
            f"Expected files: {req_id}.json or {req_id}.xlsx"
        )

    print(f"📄 Found requirement: {file_path}")

    # Parse based on extension
    if file_path.suffix == '.txt':
        spec = parse_natural_language_file(file_path)
    elif file_path.suffix == '.json':
        spec = parse_json_file(file_path)
    elif file_path.suffix in ['.xlsx', '.xls']:
        spec = parse_excel_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    return spec, file_path


def display_test_summary(spec: dict):
    """Display test specification summary."""
    print()
    print(f"  Requirement ID: {spec.get('req_id', 'N/A')}")

    meta = spec.get('suite_meta', {})
    if meta:
        print(f"  Application: {meta.get('app', 'N/A')}")
        print(f"  Area: {meta.get('area', 'N/A')}")
        print(f"  Priority: {meta.get('priority', 'N/A')}")

    testcases = spec.get('testcases', [])
    total_steps = sum(len(tc.get('steps', [])) for tc in testcases)

    print()
    print(f"  Test Cases: {len(testcases)}")
    print(f"  Total Steps: {total_steps}")

    for tc in testcases:
        print(f"    • {tc.get('tc_id', 'N/A')}: {tc.get('title', 'N/A')}")


def display_execution_results(result: RunState):
    """Display execution results in user-friendly format."""
    print_header("EXECUTION RESULTS")

    verdict = result.verdict or "unknown"

    # Verdict with color
    if verdict == "pass":
        print_success(f"Verdict: PASS")
    elif verdict == "partial":
        print_warning(f"Verdict: PARTIAL")
    else:
        print_error(f"Verdict: FAIL")

    print()
    print(f"  Steps Executed: {result.step_idx}")
    print(f"  Heal Rounds: {result.heal_round}")
    print(f"  Heal Events: {len(result.heal_events)}")

    # Show generated artifact
    if "generated_file" in result.context:
        print()
        print_success(f"Test artifact generated: {result.context['generated_file']}")

    # Show RCA if available
    rca = result.context.get('rca')
    if rca and isinstance(rca, dict):
        print()
        print(f"  Root Cause Analysis:")
        print(f"    {rca.get('message', 'N/A')}")


@click.group()
@click.version_option(version='2.0.0', prog_name='PACTS')
def cli():
    """
    PACTS - Production-Ready Autonomous Context Testing System

    Transform AI test generation from 70% to 95%+ with Find-First Verification.
    """
    pass


@cli.command()
@click.option('--req', required=True, help='Requirement ID (e.g., REQ-001, REQ-LOGIN-001)')
@click.option('--url', help='Override target URL (optional)')
@click.option('--headed/--headless', default=False, help='Run in headed mode (visible browser)')
@click.option('--slow-mo', default=0, type=int, help='Slow motion delay in milliseconds')
@click.option('--mcp/--no-mcp', default=False, help='Enable MCP Playwright integration')
def test(req: str, url: Optional[str], headed: bool, slow_mo: int, mcp: bool):
    """
    Execute test from requirement specification.

    Examples:

        pacts test --req REQ-001

        pacts test --req REQ-LOGIN-001 --headed

        pacts test --req REQ-SHOPPING-001 --slow-mo 500

        pacts test --req REQ-001 --url https://staging.example.com
    """
    print_header("PACTS - Autonomous Test Execution")

    try:
        # Load requirement spec
        print("Step 1: Loading requirement specification...")
        spec, file_path = load_requirement_spec(req)

        # Handle natural language specs
        is_natural_language = spec.get("_natural_language", False)
        if is_natural_language:
            print("  Format: Natural Language (will be parsed by LLM)")
            print(f"  Preview: {spec['natural_language_text'][:200]}...")
        else:
            display_test_summary(spec)

        # Extract URL
        # For natural language, URL will be extracted by LLM during Planner execution
        # So we defer URL validation until after Planner runs
        if not is_natural_language:
            test_url = url if url else spec.get('url') or spec.get('suite_meta', {}).get('url')

            if not test_url:
                # Try to infer from testcases
                for tc in spec.get('testcases', []):
                    if 'url' in tc:
                        test_url = tc['url']
                        break

            if not test_url:
                print_error("No URL found in specification. Use --url to specify target URL.")
                sys.exit(1)
        else:
            # Natural language mode - URL will be extracted by LLM
            test_url = url if url else None

        print()
        print(f"  Target URL: {test_url}")
        print(f"  Mode: {'HEADED (visible)' if headed else 'HEADLESS'}")
        if slow_mo > 0:
            print(f"  Slow Motion: {slow_mo}ms")
        if mcp:
            print(f"  MCP Integration: ENABLED")

        # Create RunState
        print()
        print("Step 2: Initializing PACTS pipeline...")

        # Check MCP Playwright availability and display status
        mcp_status = _check_mcp_status(mcp)
        _display_mcp_status(mcp_status)

        # Check for saved Salesforce session
        import os
        storage_state_path = "hitl/salesforce_auth.json"
        storage_state = storage_state_path if os.path.exists(storage_state_path) else None

        browser_config = {
            "headless": not headed,
            "slow_mo": slow_mo,
            "storage_state": storage_state
        }

        # Set MCP environment variable if requested
        if mcp:
            import os
            os.environ['USE_MCP'] = 'true'

        # Build context based on spec type
        context = {
            "url": test_url,
            "browser_config": browser_config
        }

        if is_natural_language:
            # Natural language mode - pass to Planner for LLM parsing
            context["natural_language"] = spec["natural_language_text"]
        else:
            # JSON/structured mode
            context["suite"] = spec

        state = RunState(
            req_id=spec.get('req_id', req),
            context=context
        )

        # Execute pipeline
        print()
        print("Step 3: Executing test pipeline...")
        print("  Pipeline: Planner → POMBuilder → Executor ↔ OracleHealer → VerdictRCA → Generator")
        print()

        result = asyncio.run(_run_pipeline_with_storage(state))

        # Extract RunState from result
        if isinstance(result, RunState):
            final_state = result
        else:
            final_state = RunState(**result)

        # Display results
        display_execution_results(final_state)

        # Exit with appropriate code
        if final_state.verdict == "pass":
            print()
            print_success("Test execution completed successfully!")
            sys.exit(0)
        elif final_state.verdict == "partial":
            print()
            print_warning("Test execution partially completed.")
            sys.exit(1)
        else:
            print()
            print_error("Test execution failed.")
            sys.exit(1)

    except FileNotFoundError as e:
        print()
        print_error(str(e))
        print()
        print("Available specs:")
        specs_dir = Path("specs")
        if specs_dir.exists():
            for file in sorted(specs_dir.glob("*")):
                print(f"  • {file.name}")
        sys.exit(1)

    except NotImplementedError as e:
        print()
        print_error(str(e))
        sys.exit(1)

    except Exception as e:
        print()
        print_error(f"Execution failed: {type(e).__name__}")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command(name='list')
def list_specs():
    """List all available requirement specifications."""
    print_header("Available Requirements")

    found = False

    # Check requirements/ directory
    req_dir = Path("requirements")
    if req_dir.exists():
        file_list = [f for f in req_dir.glob("*")]
        files = file_list
        if files:
            print("📁 requirements/")
            for file in sorted(files):
                if file.suffix in ['.json', '.xlsx', '.xls']:
                    print(f"  • {file.name}")
                    found = True
            print()

    # Check specs/ directory
    specs_dir = Path("specs")
    if specs_dir.exists():
        file_list = [f for f in specs_dir.glob("*")]
        files = file_list
        if files:
            print("📁 specs/")
            for file in sorted(files):
                if file.suffix in ['.json', '.xlsx', '.xls']:
                    print(f"  • {file.name}")
                    found = True
            print()

    if not found:
        print("No requirement files found.")
        print()
        print("Create requirement files in:")
        print("  • requirements/ (for production)")
        print("  • specs/ (for development)")


if __name__ == "__main__":
    # Fix Windows console encoding
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    cli()
