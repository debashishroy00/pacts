#!/usr/bin/env python
"""
MCP Playwright Integration - Full Validation Runner

Dead-simple automated validation of MCP integration.
Runs all 3 scenarios and reports results.
"""
import os
import sys
import subprocess
import time
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print section header."""
    print()
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.END}")
    print()


def print_step(number, text):
    """Print step header."""
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}Step {number}: {text}{Colors.END}")
    print()


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def run_command(cmd, output_file=None, env_vars=None):
    """
    Run a command and capture output.

    Args:
        cmd: Command to run (list or string)
        output_file: Optional file to save output
        env_vars: Optional environment variables to set

    Returns:
        tuple: (return_code, stdout, stderr)
    """
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    if isinstance(cmd, str):
        cmd = cmd.split()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300  # 5 minute timeout
        )

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
                f.write(result.stderr)

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out after 5 minutes"
    except Exception as e:
        return -1, "", str(e)


def check_environment():
    """Check environment variables."""
    print_step(0, "Environment Check")

    use_mcp = os.getenv("USE_MCP", "not set")
    mcp_url = os.getenv("MCP_PW_SERVER_URL", "not set")

    print(f"  USE_MCP: {use_mcp}")
    print(f"  MCP_PW_SERVER_URL: {mcp_url}")

    return mcp_url != "not set"


def check_mcp_health():
    """Check MCP server health."""
    print_step(1, "MCP Health Check")

    returncode, stdout, stderr = run_command([sys.executable, "mcp_smoke.py"])

    if returncode == 0:
        print_success("MCP server is responding")
        return True
    else:
        print_warning("MCP server not responding (will test fallback)")
        return False


def run_scenario_a():
    """Run Scenario A: MCP Enabled."""
    print_step(2, "Scenario A - MCP Enabled")

    print_info("Running headed test with MCP enabled...")
    returncode, stdout, stderr = run_command(
        [sys.executable, "run_e2e_headed.py"],
        output_file="out_mcp_on.txt",
        env_vars={"USE_MCP": "true"}
    )

    print(f"  Output saved to: out_mcp_on.txt")

    # Analyze output
    with open("out_mcp_on.txt", 'r') as f:
        output = f.read()

    mcp_calls = output.count("MCP")
    has_verdict = "Verdict:" in output
    has_steps = "Steps Executed:" in output

    print(f"  MCP calls detected: {mcp_calls}")

    if has_verdict:
        verdict_line = [l for l in output.split('\n') if 'Verdict:' in l]
        if verdict_line:
            print(f"  {verdict_line[-1].strip()}")

    if has_steps:
        steps_line = [l for l in output.split('\n') if 'Steps Executed:' in l]
        if steps_line:
            print(f"  {steps_line[-1].strip()}")

    if returncode == 0 and mcp_calls > 0:
        print_success("Scenario A passed with MCP integration")
        return True
    elif returncode == 0:
        print_warning("Scenario A passed but no MCP calls detected")
        return False
    else:
        print_error("Scenario A failed")
        return False


def run_scenario_b():
    """Run Scenario B: MCP Disabled (Fallback)."""
    print_step(3, "Scenario B - MCP Disabled (Fallback)")

    print_info("Running headed test with MCP disabled...")
    returncode, stdout, stderr = run_command(
        [sys.executable, "run_e2e_headed.py"],
        output_file="out_mcp_off.txt",
        env_vars={"USE_MCP": "false"}
    )

    print(f"  Output saved to: out_mcp_off.txt")

    # Analyze output
    with open("out_mcp_off.txt", 'r') as f:
        output = f.read()

    mcp_calls = output.count("MCP")
    has_verdict = "Verdict:" in output
    has_steps = "Steps Executed:" in output

    print(f"  MCP calls detected: {mcp_calls} (should be 0)")

    if has_verdict:
        verdict_line = [l for l in output.split('\n') if 'Verdict:' in l]
        if verdict_line:
            print(f"  {verdict_line[-1].strip()}")

    if has_steps:
        steps_line = [l for l in output.split('\n') if 'Steps Executed:' in l]
        if steps_line:
            print(f"  {steps_line[-1].strip()}")

    if returncode == 0 and mcp_calls == 0:
        print_success("Scenario B passed with clean fallback")
        return True
    elif returncode == 0:
        print_warning("Scenario B passed but MCP calls detected (unexpected)")
        return False
    else:
        print_error("Scenario B failed")
        return False


def check_artifacts():
    """Check generated artifacts."""
    print_step(4, "Artifacts Check")

    returncode, stdout, stderr = run_command([sys.executable, "plan_smoke.py"])

    print(stdout)

    if returncode == 0:
        print_success("All artifacts validated")
        return True
    else:
        print_error("Artifact validation failed")
        return False


def print_summary(results):
    """Print validation summary."""
    print_header("Validation Summary")

    all_passed = all(results.values())

    for scenario, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        color = Colors.GREEN if passed else Colors.RED
        print(f"  {color}{status}{Colors.END} - {scenario}")

    print()

    if all_passed:
        print_success("🎉 ALL VALIDATIONS PASSED")
        print()
        print("Next Steps:")
        print("  1. Review logs: out_mcp_on.txt, out_mcp_off.txt")
        print("  2. Inspect artifacts: ls generated_tests/")
        print("  3. Ready for merge! 🚀")
        return 0
    else:
        print_error("⚠️  SOME VALIDATIONS FAILED")
        print()
        print("Troubleshooting:")
        print("  1. Review failed scenario logs")
        print("  2. Check VALIDATE-MCP.md for triage steps")
        print("  3. Verify MCP server is running (if applicable)")
        return 1


def main():
    """Main validation runner."""
    print_header("MCP Playwright Integration - Full Validation")

    results = {}

    # Step 0: Environment check
    has_mcp_config = check_environment()

    # Step 1: Health check
    mcp_available = check_mcp_health()

    # Step 2: Scenario A (MCP ON)
    if mcp_available:
        results["Scenario A (MCP ON)"] = run_scenario_a()
    else:
        print_warning("Skipping Scenario A (MCP server unavailable)")
        results["Scenario A (MCP ON)"] = False

    # Step 3: Scenario B (MCP OFF / Fallback)
    results["Scenario B (Fallback)"] = run_scenario_b()

    # Step 4: Artifacts
    results["Artifacts"] = check_artifacts()

    # Summary
    exit_code = print_summary(results)

    print()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
