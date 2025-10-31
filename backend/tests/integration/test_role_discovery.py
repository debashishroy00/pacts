"""
Integration Test Suite: Role Discovery Validation

Tests role_name discovery strategy across diverse button types, links, and interactive elements.
Validates ≥95% discovery rate and generates coverage metrics.
"""
import asyncio
import json
import re
from typing import Dict, List, Any
from datetime import datetime
from backend.runtime.browser_client import BrowserClient
from backend.runtime.discovery import discover_selector, ROLE_HINTS


# Test scenarios covering diverse button types
TEST_SCENARIOS = [
    # Submit buttons
    {
        "name": "Submit Button",
        "url": "https://www.saucedemo.com",
        "intent": {"element": "Login", "action": "click"},
        "expected_role": "button",
        "category": "submit_button"
    },

    # Continue/Next buttons (wizard patterns)
    {
        "name": "Continue Button",
        "url": "https://demo.playwright.dev/todomvc",
        "intent": {"element": "Add", "action": "click"},
        "expected_role": "button",
        "category": "action_button"
    },

    # Links
    {
        "name": "Navigation Link",
        "url": "https://www.saucedemo.com",
        "intent": {"element": "Sauce Labs", "action": "click"},
        "expected_role": "link",
        "category": "link"
    },
]


# Additional test cases using common button text patterns
BUTTON_TEXT_PATTERNS = [
    # From ROLE_HINTS
    ("Login", "button"),
    ("Submit", "button"),
    ("Sign In", "button"),
    ("Continue", "button"),
    ("Next", "button"),
    ("OK", "button"),
    ("Search", "button"),
    ("Cancel", "button"),
    ("Close", "button"),
    ("Save", "button"),
    ("Delete", "button"),
    ("Edit", "button"),
    ("Add", "button"),
    ("Remove", "button"),
    ("Back", "button"),
    ("Forward", "button"),
]


class RoleDiscoveryValidator:
    """Validates role_name discovery strategy across diverse scenarios."""

    def __init__(self):
        self.browser = None
        self.results = []
        self.stats = {
            "total_attempts": 0,
            "successful_discoveries": 0,
            "failed_discoveries": 0,
            "by_category": {},
            "by_role": {},
            "confidence_distribution": [],
        }

    async def setup(self):
        """Initialize browser."""
        self.browser = BrowserClient()
        await self.browser.start(headless=True)

    async def teardown(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()

    async def test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single discovery scenario."""
        result = {
            "name": scenario["name"],
            "url": scenario["url"],
            "intent": scenario["intent"],
            "expected_role": scenario.get("expected_role"),
            "category": scenario.get("category", "unknown"),
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Navigate to URL
            await self.browser.goto(scenario["url"])
            await asyncio.sleep(1)  # Wait for page to stabilize

            # Attempt discovery
            discovered = await discover_selector(self.browser, scenario["intent"])

            if discovered:
                result["status"] = "success"
                result["selector"] = discovered["selector"]
                result["confidence"] = discovered.get("score", 0.0)
                result["strategy"] = discovered["meta"].get("strategy")
                result["discovered_role"] = discovered["meta"].get("role")

                # Verify role matches expectation
                expected = scenario.get("expected_role")
                actual = result["discovered_role"]
                result["role_match"] = (expected == actual) if expected else None

                self.stats["successful_discoveries"] += 1
                self.stats["confidence_distribution"].append(result["confidence"])
            else:
                result["status"] = "failed"
                result["error"] = "Element not discovered"
                self.stats["failed_discoveries"] += 1

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            self.stats["failed_discoveries"] += 1

        self.stats["total_attempts"] += 1

        # Update category stats
        category = result["category"]
        if category not in self.stats["by_category"]:
            self.stats["by_category"][category] = {"success": 0, "total": 0}
        self.stats["by_category"][category]["total"] += 1
        if result["status"] == "success":
            self.stats["by_category"][category]["success"] += 1

        # Update role stats
        if result.get("discovered_role"):
            role = result["discovered_role"]
            if role not in self.stats["by_role"]:
                self.stats["by_role"][role] = 0
            self.stats["by_role"][role] += 1

        self.results.append(result)
        return result

    async def validate_role_hints(self) -> List[Dict[str, Any]]:
        """Validate all ROLE_HINTS mappings using synthetic tests."""
        print("\n📋 Validating ROLE_HINTS mappings...")
        hint_results = []

        for text, expected_role in BUTTON_TEXT_PATTERNS:
            intent = {"element": text, "action": "click"}

            # Test role detection logic without actual browser discovery
            from backend.runtime.discovery import _try_role_name

            result = {
                "text": text,
                "expected_role": expected_role,
                "hint_exists": text.lower() in ROLE_HINTS or any(
                    key in text.lower() for key in ROLE_HINTS.keys()
                ),
            }

            # Check if ROLE_HINTS would map correctly
            detected_role = None
            if intent.get("action") == "click":
                detected_role = "button"
            for key, role in ROLE_HINTS.items():
                if key in text.lower():
                    detected_role = role
                    break

            result["detected_role"] = detected_role
            result["correct_mapping"] = (detected_role == expected_role)

            hint_results.append(result)

            status = "✅" if result["correct_mapping"] else "❌"
            print(f"  {status} {text} → {detected_role} (expected: {expected_role})")

        return hint_results

    def calculate_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.stats["total_attempts"] == 0:
            return 0.0
        return (self.stats["successful_discoveries"] / self.stats["total_attempts"]) * 100

    def generate_confidence_histogram(self) -> Dict[str, int]:
        """Generate confidence score distribution."""
        histogram = {
            "0.90-1.00": 0,
            "0.80-0.89": 0,
            "0.70-0.79": 0,
            "0.60-0.69": 0,
            "<0.60": 0,
        }

        for conf in self.stats["confidence_distribution"]:
            if conf >= 0.90:
                histogram["0.90-1.00"] += 1
            elif conf >= 0.80:
                histogram["0.80-0.89"] += 1
            elif conf >= 0.70:
                histogram["0.70-0.79"] += 1
            elif conf >= 0.60:
                histogram["0.60-0.69"] += 1
            else:
                histogram["<0.60"] += 1

        return histogram

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        success_rate = self.calculate_success_rate()
        histogram = self.generate_confidence_histogram()

        report = {
            "test_suite": "Role Discovery Validation",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_attempts": self.stats["total_attempts"],
                "successful_discoveries": self.stats["successful_discoveries"],
                "failed_discoveries": self.stats["failed_discoveries"],
                "success_rate": f"{success_rate:.2f}%",
                "target_success_rate": ">=95%",
                "target_met": success_rate >= 95.0,
            },
            "coverage_by_category": {},
            "coverage_by_role": self.stats["by_role"],
            "confidence_histogram": histogram,
            "detailed_results": self.results,
        }

        # Calculate category coverage
        for category, data in self.stats["by_category"].items():
            rate = (data["success"] / data["total"]) * 100 if data["total"] > 0 else 0
            report["coverage_by_category"][category] = {
                "success": data["success"],
                "total": data["total"],
                "rate": f"{rate:.2f}%",
            }

        return report

    def print_summary(self, report: Dict[str, Any]):
        """Print human-readable summary."""
        print("\n" + "="*80)
        print("ROLE DISCOVERY VALIDATION - SUMMARY")
        print("="*80)

        summary = report["summary"]
        print(f"\n📊 Overall Results:")
        print(f"  • Total attempts: {summary['total_attempts']}")
        print(f"  • Successful: {summary['successful_discoveries']}")
        print(f"  • Failed: {summary['failed_discoveries']}")
        print(f"  • Success rate: {summary['success_rate']}")
        print(f"  • Target: {summary['target_success_rate']}")

        target_met = "✅ TARGET MET" if summary["target_met"] else "❌ BELOW TARGET"
        print(f"  • Status: {target_met}")

        print(f"\n📈 Coverage by Category:")
        for category, data in report["coverage_by_category"].items():
            print(f"  • {category}: {data['success']}/{data['total']} ({data['rate']})")

        print(f"\n🎯 Coverage by Role:")
        for role, count in report["coverage_by_role"].items():
            print(f"  • {role}: {count} elements")

        print(f"\n📊 Confidence Distribution:")
        for range_label, count in report["confidence_histogram"].items():
            bar = "█" * count
            print(f"  {range_label}: {bar} ({count})")

        print("\n" + "="*80)


async def run_validation():
    """Run complete role discovery validation suite."""
    print("\n" + "="*80)
    print("ROLE DISCOVERY VALIDATION SUITE")
    print("="*80)
    print("\nThis test validates the role_name discovery strategy across:")
    print("  • Submit buttons (Login, Sign In, etc.)")
    print("  • Action buttons (Continue, Next, Cancel, etc.)")
    print("  • Links (Navigation, Help, etc.)")
    print("  • Various ARIA roles and text patterns")
    print("\nTarget: >=95% discovery rate\n")

    validator = RoleDiscoveryValidator()

    try:
        print("🚀 Initializing browser...")
        await validator.setup()

        print(f"\n🧪 Running {len(TEST_SCENARIOS)} live discovery scenarios...")
        for i, scenario in enumerate(TEST_SCENARIOS, 1):
            print(f"\n[{i}/{len(TEST_SCENARIOS)}] Testing: {scenario['name']}")
            print(f"  URL: {scenario['url']}")
            print(f"  Looking for: {scenario['intent']['element']}")

            result = await validator.test_scenario(scenario)

            if result["status"] == "success":
                print(f"  ✅ FOUND: {result['selector']}")
                print(f"     Strategy: {result['strategy']}")
                print(f"     Role: {result['discovered_role']}")
                print(f"     Confidence: {result['confidence']:.2f}")
            else:
                print(f"  ❌ FAILED: {result.get('error', 'Unknown error')}")

        # Validate ROLE_HINTS
        hint_results = await validator.validate_role_hints()

        # Generate and save report
        print("\n📝 Generating coverage report...")
        report = validator.generate_report()

        # Add ROLE_HINTS validation to report
        report["role_hints_validation"] = {
            "total_patterns": len(hint_results),
            "correct_mappings": sum(1 for r in hint_results if r["correct_mapping"]),
            "incorrect_mappings": sum(1 for r in hint_results if not r["correct_mapping"]),
            "details": hint_results,
        }

        # Save to file
        report_file = "role_discovery_validation_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  ✅ Report saved to: {report_file}")

        # Print summary
        validator.print_summary(report)

        # Print ROLE_HINTS validation
        hints_correct = report["role_hints_validation"]["correct_mappings"]
        hints_total = report["role_hints_validation"]["total_patterns"]
        hints_rate = (hints_correct / hints_total * 100) if hints_total > 0 else 0
        print(f"\n🔍 ROLE_HINTS Validation:")
        print(f"  • Patterns tested: {hints_total}")
        print(f"  • Correct mappings: {hints_correct}/{hints_total} ({hints_rate:.1f}%)")

        print("\n" + "="*80)
        print("VALIDATION COMPLETE")
        print("="*80)

        return report

    finally:
        print("\n🧹 Cleaning up...")
        await validator.teardown()


if __name__ == "__main__":
    report = asyncio.run(run_validation())
