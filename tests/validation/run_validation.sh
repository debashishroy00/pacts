#!/bin/bash
# PACTS v3.1s Phase 4 Validation Runner
# Executes complete validation matrix and generates report

set -e  # Exit on error

echo "======================================================================"
echo "  PACTS v3.1s - Phase 4 Validation Matrix"
echo "======================================================================"
echo ""
echo "Starting validation at $(date)"
echo ""

# Environment check
echo "[1/6] Environment sanity check..."
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Using defaults."
fi

# Verify stealth mode is enabled
export PACTS_STEALTH=true
export PACTS_TZ=America/New_York
export PACTS_LOCALE=en-US

echo "✅ Environment configured:"
echo "   PACTS_STEALTH=${PACTS_STEALTH}"
echo "   PACTS_TZ=${PACTS_TZ}"
echo "   PACTS_LOCALE=${PACTS_LOCALE}"
echo ""

# Create validation output directory
VALIDATION_DIR="runs/validation_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$VALIDATION_DIR"
echo "📁 Results will be saved to: $VALIDATION_DIR"
echo ""

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a validation suite
run_suite() {
    local suite_name=$1
    local suite_file=$2
    local extra_args=${3:-""}

    echo "======================================================================"
    echo "  Running: $suite_name"
    echo "======================================================================"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if pacts test "$suite_file" $extra_args 2>&1 | tee "$VALIDATION_DIR/${suite_name}.log"; then
        echo "✅ $suite_name PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ $suite_name FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo ""
}

# Run validation suites
echo "[2/6] Running Static Sites validation..."
run_suite "static_sites" "tests/validation/static_sites.yaml"

echo "[3/6] Running SPA Sites validation..."
run_suite "spa_sites" "tests/validation/spa_sites.yaml"

echo "[4/6] Running Auth Flows validation..."
run_suite "auth_flows" "tests/validation/auth_flows.yaml"

echo "[5/6] Running Multi-Dataset validation..."
run_suite "multi_dataset" "tests/validation/multi_dataset.yaml" "--data tests/validation/users.csv"

echo "[6/6] Running Full Parallel validation..."
run_suite "full_parallel" "tests/validation/" "--parallel=3"

# Generate summary
echo "======================================================================"
echo "  VALIDATION SUMMARY"
echo "======================================================================"
echo ""
echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $FAILED_TESTS"
echo ""

PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED_TESTS / $TOTAL_TESTS) * 100}")
echo "Pass Rate: ${PASS_RATE}%"
echo ""

# Create summary file
cat > "$VALIDATION_DIR/summary.txt" <<EOF
PACTS v3.1s Phase 4 Validation Summary
=======================================

Date: $(date)
Environment:
  - PACTS_STEALTH: ${PACTS_STEALTH}
  - PACTS_TZ: ${PACTS_TZ}
  - PACTS_LOCALE: ${PACTS_LOCALE}

Results:
  - Total Tests: $TOTAL_TESTS
  - Passed: $PASSED_TESTS
  - Failed: $FAILED_TESTS
  - Pass Rate: ${PASS_RATE}%

Success Criteria:
  - Pass Rate Target: ≥95%
  - Avg Step Duration: <2s (static), <3s (SPA)
  - Retry Rate: <5%
  - Blocked Headless: <10%

Status: $([ "$PASS_RATE" \> "95" ] && echo "✅ PASSED" || echo "❌ FAILED")

Logs: $VALIDATION_DIR/
EOF

cat "$VALIDATION_DIR/summary.txt"

# Exit code based on pass rate
if [ "$PASS_RATE" = "100.0" ]; then
    echo ""
    echo "🎉 All validation tests passed! v3.1s is production-ready."
    exit 0
elif awk "BEGIN {exit !($PASS_RATE >= 95)}"; then
    echo ""
    echo "✅ Validation passed (≥95% pass rate). Review failures in logs."
    exit 0
else
    echo ""
    echo "❌ Validation failed (<95% pass rate). Review logs and fix issues."
    exit 1
fi
