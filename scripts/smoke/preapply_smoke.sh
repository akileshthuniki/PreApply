#!/usr/bin/env bash
# Minimal smoke test for PreApply - regression protection without test framework complexity
# Usage: ./scripts/smoke/preapply_smoke.sh

set -euo pipefail  # Exit on error, undefined vars, pipe failures

echo "PreApply Smoke Test"
echo "==================="
echo ""

# Test 1: Basic analysis
echo "✓ Test 1: Basic analysis"
preapply analyze samples/low_risk.json > /dev/null 2>&1
echo "  PASS: analyze command works"

# Test 2: Explain (overall)
echo "✓ Test 2: Explain (overall)"
preapply explain samples/low_risk.json > /dev/null 2>&1
echo "  PASS: explain command works"

# Test 3: Explain (JSON output)
echo "✓ Test 3: Explain (JSON output)"
preapply explain samples/low_risk.json --json > /dev/null 2>&1
echo "  PASS: explain --json works"

# Test 3b: JSON contract sanity check
echo "✓ Test 3b: JSON contract sanity"
if command -v jq > /dev/null 2>&1; then
    preapply explain samples/low_risk.json --json \
        | jq -e '.explanation_id and .risk_level' > /dev/null 2>&1
    echo "  PASS: JSON contains core contract fields"
else
    echo "  SKIP: jq not available (JSON validation skipped)"
fi

# Test 4: List resources
echo "✓ Test 4: List resources"
preapply explain samples/low_risk.json --list-resources > /dev/null 2>&1
echo "  PASS: explain --list-resources works"

# Test 5: Summary
echo "✓ Test 5: Summary"
preapply summary samples/low_risk.json > /dev/null 2>&1
echo "  PASS: summary command works"

# Test 6: Policy check (if policy file exists)
if [ -f "policy.example.yaml" ]; then
    echo "✓ Test 6: Policy check (auto mode)"
    preapply policy check samples/low_risk.json \
        --policy-file policy.example.yaml \
        --enforcement-mode auto > /dev/null 2>&1 || {
        exit_code=$?
        if [ "$exit_code" -eq 1 ]; then
            echo "  FAIL: policy check runtime error (exit code $exit_code)"
            exit 1
        elif [ "$exit_code" -eq 2 ]; then
            # Exit code 2 = policy violation in auto mode (acceptable for smoke test)
            echo "  PASS: policy check returns exit code 2 (auto-block) on violations"
        elif [ "$exit_code" -eq 3 ]; then
            echo "  WARN: policy check returned exit code 3 (unexpected in auto mode)"
        else
            echo "  FAIL: unexpected exit code $exit_code"
            exit 1
        fi
    }
    echo "  PASS: policy check command works (auto mode)"
    
    # Test 6b: Policy check with manual mode
    echo "✓ Test 6b: Policy check (manual mode)"
    preapply policy check samples/low_risk.json \
        --policy-file policy.example.yaml \
        --enforcement-mode manual > /dev/null 2>&1 || {
        exit_code=$?
        if [ "$exit_code" -eq 1 ]; then
            echo "  FAIL: policy check runtime error (exit code $exit_code)"
            exit 1
        elif [ "$exit_code" -eq 3 ]; then
            # Exit code 3 = policy violation in manual mode (expected behavior)
            echo "  PASS: policy check returns exit code 3 (approval required) on violations"
        elif [ "$exit_code" -eq 2 ]; then
            echo "  WARN: policy check returned exit code 2 (unexpected in manual mode)"
        else
            echo "  FAIL: unexpected exit code $exit_code"
            exit 1
        fi
    }
    echo "  PASS: policy check command works (manual mode)"
fi

echo ""
echo "==================="
echo "All smoke tests passed ✓"

