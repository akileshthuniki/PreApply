#!/usr/bin/env bash
# Generic CI/CD policy check script for PreApply
# Works with any CI/CD platform (GitHub Actions, GitLab CI, Jenkins, etc.)
#
# Usage:
#   ./scripts/ci/policy-check.sh <plan.json> <policy.yaml> [environment-config.yaml]

set -euo pipefail

# Colors for output (optional, CI-friendly)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Arguments
PLAN_FILE="${1:-}"
POLICY_FILE="${2:-}"
ENV_CONFIG="${3:-}"

# Validate arguments
if [ -z "$PLAN_FILE" ] || [ -z "$POLICY_FILE" ]; then
    echo "Usage: $0 <plan.json> <policy.yaml> [environment-config.yaml]"
    echo ""
    echo "Arguments:"
    echo "  plan.json              - Terraform plan JSON file"
    echo "  policy.yaml            - Policy YAML file"
    echo "  environment-config.yaml - Optional: Path to .preapply-env.yaml"
    exit 1
fi

# Check if files exist
if [ ! -f "$PLAN_FILE" ]; then
    echo -e "${RED}Error: Plan file not found: $PLAN_FILE${NC}" >&2
    exit 1
fi

if [ ! -f "$POLICY_FILE" ]; then
    echo -e "${RED}Error: Policy file not found: $POLICY_FILE${NC}" >&2
    exit 1
fi

# Build command
CMD="preapply policy check \"$PLAN_FILE\" --policy-file \"$POLICY_FILE\""

# Add environment config if provided
if [ -n "$ENV_CONFIG" ]; then
    CMD="$CMD --environment \"$ENV_CONFIG\""
fi

# Run policy check
echo "Running PreApply policy check..."
echo "  Plan: $PLAN_FILE"
echo "  Policy: $POLICY_FILE"
if [ -n "$ENV_CONFIG" ]; then
    echo "  Environment: $ENV_CONFIG"
fi
echo ""

EXIT_CODE=0
$CMD || EXIT_CODE=$?

# Handle exit codes
case $EXIT_CODE in
    0)
        echo -e "${GREEN}✓ Policy check passed${NC}"
        exit 0
        ;;
    1)
        echo -e "${RED}✗ Runtime error during policy check${NC}" >&2
        exit 1
        ;;
    2)
        echo -e "${RED}✗ Policy violations detected (auto-block)${NC}" >&2
        echo "Deployment blocked due to policy violations."
        exit 2
        ;;
    3)
        echo -e "${YELLOW}⚠ Policy violations detected (approval required)${NC}" >&2
        echo "Manual approval required to proceed with deployment."
        echo ""
        echo "This exit code (3) signals that CI/CD should pause and wait for approval."
        echo "The CI/CD platform should handle the approval workflow."
        exit 3
        ;;
    *)
        echo -e "${RED}✗ Unexpected exit code: $EXIT_CODE${NC}" >&2
        exit 1
        ;;
esac

