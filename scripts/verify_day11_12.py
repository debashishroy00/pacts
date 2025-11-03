"""
Verify Day 11-12 Implementation

Quick checks to ensure:
1. HealHistory integration in OracleHealer
2. RunStorage wiring in build_graph
3. Metrics endpoints available
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_file_modified(filepath: str, expected_lines: list[str]) -> bool:
    """Check if file contains expected modifications."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            for line in expected_lines:
                if line not in content:
                    return False
        return True
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False


def check_file_exists(filepath: str) -> bool:
    """Check if file exists."""
    return Path(filepath).exists()


def main():
    print("=" * 70)
    print("PACTS v3.0 - Day 11-12 Verification")
    print("=" * 70)
    print()

    checks = []

    # Check 1: OracleHealer has HealHistory integration
    print("[CHECK] Checking HealHistory integration in OracleHealer...")
    healer_checks = [
        "from ..storage.init import get_storage",
        "heal_history = storage.heal_history",
        "await heal_history.get_best_strategy",
        "await heal_history.record_outcome"
    ]
    healer_ok = check_file_modified(
        "backend/agents/oracle_healer.py",
        healer_checks
    )
    checks.append(("HealHistory in OracleHealer", healer_ok))
    if healer_ok:
        print("  ✅ HealHistory query and record found")
    else:
        print("  ❌ HealHistory integration incomplete")

    # Check 2: RunStorage wiring in build_graph
    print("\n[CHECK] Checking RunStorage wiring in build_graph...")
    graph_checks = [
        "from ..storage.init import get_storage",
        "storage.runs",
        "await run_storage.create_run",
        "await run_storage.update_run",
        "await run_storage.save_artifact"
    ]
    graph_ok = check_file_modified(
        "backend/graph/build_graph.py",
        graph_checks
    )
    checks.append(("RunStorage in build_graph", graph_ok))
    if graph_ok:
        print("  ✅ RunStorage create, update, and artifacts found")
    else:
        print("  ❌ RunStorage wiring incomplete")

    # Check 3: Metrics endpoint exists
    print("\n[CHECK] Checking metrics endpoint...")
    metrics_ok = check_file_exists("backend/api/metrics.py")
    checks.append(("Metrics endpoint", metrics_ok))
    if metrics_ok:
        # Check router has expected endpoints
        router_checks = [
            "@router.get(\"/cache\")",
            "@router.get(\"/heal\")",
            "@router.get(\"/runs\")",
            "@router.get(\"/summary\")"
        ]
        router_ok = check_file_modified(
            "backend/api/metrics.py",
            router_checks
        )
        if router_ok:
            print("  ✅ Metrics router with 4 endpoints found")
        else:
            print("  ⚠️  Metrics file exists but endpoints incomplete")
            checks.append(("Metrics endpoints complete", False))
    else:
        print("  ❌ Metrics endpoint file not found")

    # Check 4: Metrics mounted in main.py
    print("\n[CHECK] Checking metrics router mounted...")
    main_checks = [
        "from .metrics import router as metrics_router",
        "app.include_router(metrics_router)"
    ]
    main_ok = check_file_modified(
        "backend/api/main.py",
        main_checks
    )
    checks.append(("Metrics router mounted", main_ok))
    if main_ok:
        print("  ✅ Metrics router mounted in FastAPI app")
    else:
        print("  ❌ Metrics router not mounted")

    # Check 5: CLI metrics script exists
    print("\n[CHECK] Checking CLI metrics script...")
    cli_ok = check_file_exists("scripts/print_metrics.py")
    checks.append(("CLI metrics script", cli_ok))
    if cli_ok:
        print("  ✅ scripts/print_metrics.py found")
    else:
        print("  ❌ CLI metrics script not found")

    # Check 6: Documentation exists
    print("\n[CHECK] Checking documentation...")
    docs_ok = check_file_exists("docs/DAY-11-12-NOTES.md")
    checks.append(("Documentation", docs_ok))
    if docs_ok:
        print("  ✅ docs/DAY-11-12-NOTES.md found")
    else:
        print("  ❌ Documentation not found")

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)

    for check_name, ok in checks:
        status = "✅" if ok else "❌"
        print(f"{status} {check_name}")

    print()
    print(f"Result: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! Day 11-12 implementation verified.")
        print("\nNext steps:")
        print("1. Run tests: docker-compose run --rm pacts-runner python -m backend.cli.main test --req wikipedia_search")
        print("2. Check metrics: python scripts/print_metrics.py")
        print("3. Verify HealHistory learning in logs")
        return 0
    else:
        print("\n⚠️  Some checks failed. Review implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
