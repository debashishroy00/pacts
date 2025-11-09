"""
PACTS v3.1s - Friendly CLI Runner

Simple, user-friendly command line interface for running tests.

Usage:
    pacts test <file-or-folder> [options]
    pacts test tests/github_login.yaml
    pacts test tests/
    pacts test tests/**/*.yaml --parallel=2

Features:
- Auto-discovery of tests/ folder
- Glob pattern support
- Pretty console output with progress
- CI-ready exit codes (0 = all pass, 1 = any fail)
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from pathlib import Path
import asyncio
import sys
import glob
import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()


def discover_tests(path_pattern: str) -> List[Path]:
    """
    Discover test files matching the given pattern.

    Args:
        path_pattern: File path, directory, or glob pattern

    Returns:
        List of test file paths

    Examples:
        discover_tests("tests/") -> all .txt files in tests/
        discover_tests("tests/**/*.yaml") -> all .yaml files recursively
        discover_tests("tests/github_*.txt") -> all github_* files
    """
    path = Path(path_pattern)

    # Case 1: Specific file
    if path.is_file():
        return [path]

    # Case 2: Directory - find all .txt files
    if path.is_dir():
        txt_files = list(path.rglob("*.txt"))
        yaml_files = list(path.rglob("*.yaml"))
        yml_files = list(path.rglob("*.yml"))
        return sorted(txt_files + yaml_files + yml_files)

    # Case 3: Glob pattern
    matches = glob.glob(path_pattern, recursive=True)
    return sorted([Path(m) for m in matches if Path(m).is_file()])


async def run_test_file(
    test_path: Path,
    browser: str = "chromium",
    headless: bool = True,
    retries: int = 0,
    data_file: Optional[str] = None,
    vars_override: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Run a single test file.

    Args:
        test_path: Path to test file
        browser: Browser type (chromium, firefox, webkit)
        headless: Run headless
        retries: Number of retries on failure
        data_file: Path to dataset file (CSV/JSONL/YAML)
        vars_override: Variable overrides from CLI

    Returns:
        Test result dictionary with status, duration, errors
    """
    from backend.cli.main import run_test_from_cli

    start_time = time.time()

    try:
        # Run the test using existing CLI infrastructure
        result = await run_test_from_cli(
            req_file=str(test_path),
            headless=headless,
            browser=browser,
            loops=1,
            cache=True,
            no_cache=False
        )

        duration = time.time() - start_time

        return {
            "file": test_path.name,
            "status": "PASS" if result.get("success") else "FAIL",
            "duration": duration,
            "steps": result.get("steps_executed", 0),
            "errors": result.get("errors", [])
        }

    except Exception as e:
        duration = time.time() - start_time
        return {
            "file": test_path.name,
            "status": "ERROR",
            "duration": duration,
            "steps": 0,
            "errors": [str(e)]
        }


async def run_tests_parallel(
    test_files: List[Path],
    parallel: int,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Run multiple tests in parallel.

    Args:
        test_files: List of test file paths
        parallel: Number of parallel workers
        **kwargs: Additional arguments for run_test_file

    Returns:
        List of test results
    """
    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(parallel)

    async def run_with_semaphore(test_path):
        async with semaphore:
            return await run_test_file(test_path, **kwargs)

    # Run all tests with concurrency limit
    tasks = [run_with_semaphore(path) for path in test_files]
    return await asyncio.gather(*tasks)


def print_summary(results: List[Dict[str, Any]]):
    """
    Print pretty summary of test results.

    Args:
        results: List of test result dictionaries
    """
    # Create summary table
    table = Table(title="Test Results Summary", show_header=True, header_style="bold magenta")
    table.add_column("Test File", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Duration", justify="right")
    table.add_column("Steps", justify="right")

    total_duration = 0
    pass_count = 0
    fail_count = 0
    error_count = 0

    for result in results:
        status = result["status"]
        duration = result["duration"]
        total_duration += duration

        # Color-code status
        if status == "PASS":
            status_display = "[green]✅ PASS[/green]"
            pass_count += 1
        elif status == "FAIL":
            status_display = "[yellow]⚠️  FAIL[/yellow]"
            fail_count += 1
        else:
            status_display = "[red]❌ ERROR[/red]"
            error_count += 1

        table.add_row(
            result["file"],
            status_display,
            f"{duration:.2f}s",
            str(result["steps"])
        )

    console.print(table)

    # Overall summary
    total = len(results)
    summary_text = f"""
[bold]Overall Results:[/bold]
  Total tests: {total}
  Passed: [green]{pass_count}[/green]
  Failed: [yellow]{fail_count}[/yellow]
  Errors: [red]{error_count}[/red]
  Total duration: {total_duration:.2f}s
"""

    if fail_count == 0 and error_count == 0:
        panel_style = "green"
        emoji = "🎉"
    else:
        panel_style = "yellow"
        emoji = "⚠️ "

    console.print(Panel(summary_text, title=f"{emoji} Test Summary", border_style=panel_style))

    # Print errors if any
    for result in results:
        if result["errors"]:
            console.print(f"\n[red]Errors in {result['file']}:[/red]")
            for error in result["errors"]:
                console.print(f"  {error}")


async def run_tests_cli(
    path: str = "tests/",
    browser: str = "chromium",
    headless: bool = True,
    retries: int = 0,
    parallel: int = 1,
    data: Optional[str] = None,
    vars: Optional[str] = None
) -> int:
    """
    Main entry point for CLI test runner.

    Args:
        path: File path, directory, or glob pattern
        browser: Browser type
        headless: Run headless
        retries: Number of retries
        parallel: Number of parallel workers
        data: Path to dataset file
        vars: Variable overrides (key=value,key2=value2)

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    # Parse variable overrides
    vars_override = {}
    if vars:
        for pair in vars.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                vars_override[key.strip()] = value.strip()

    # Discover test files
    console.print(f"[bold cyan]Discovering tests:[/bold cyan] {path}")
    test_files = discover_tests(path)

    if not test_files:
        console.print(f"[red]No test files found matching:[/red] {path}")
        return 1

    console.print(f"[green]Found {len(test_files)} test file(s)[/green]\n")

    # Run tests
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Running tests...", total=len(test_files))

        if parallel > 1:
            console.print(f"[blue]Running {parallel} tests in parallel[/blue]")
            results = await run_tests_parallel(
                test_files,
                parallel=parallel,
                browser=browser,
                headless=headless,
                retries=retries,
                data_file=data,
                vars_override=vars_override
            )
            progress.update(task, advance=len(test_files))
        else:
            results = []
            for test_file in test_files:
                result = await run_test_file(
                    test_file,
                    browser=browser,
                    headless=headless,
                    retries=retries,
                    data_file=data,
                    vars_override=vars_override
                )
                results.append(result)
                progress.update(task, advance=1)

    # Print summary
    console.print("\n")
    print_summary(results)

    # Return exit code
    failures = sum(1 for r in results if r["status"] != "PASS")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PACTS v3.1s - Friendly CLI Test Runner")
    parser.add_argument("path", nargs="?", default="tests/", help="Test file, directory, or glob pattern")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium", help="Browser type")
    parser.add_argument("--headless", type=lambda x: x.lower() != "false", default=True, help="Run headless (default: true)")
    parser.add_argument("--retries", type=int, default=0, help="Number of retries on failure")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel workers")
    parser.add_argument("--data", type=str, help="Path to dataset file (CSV/JSONL/YAML)")
    parser.add_argument("--vars", type=str, help="Variable overrides (key=value,key2=value2)")

    args = parser.parse_args()

    exit_code = asyncio.run(run_tests_cli(
        path=args.path,
        browser=args.browser,
        headless=args.headless,
        retries=args.retries,
        parallel=args.parallel,
        data=args.data,
        vars=args.vars
    ))

    sys.exit(exit_code)
