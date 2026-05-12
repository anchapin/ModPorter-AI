#!/bin/bash
# Repo Drift Sweeper CI Wrapper
# Run this in CI to detect drift before merges
#
# Usage:
#   ./scripts/repo-drift-sweeper.sh           # Report only
#   ./scripts/repo-drift-sweeper.sh --fix    # Auto-fix where safe
#   DRIFT_THRESHOLD=50 ./scripts/repo-drift-sweeper.sh  # Custom threshold

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default thresholds
DRIFT_THRESHOLD="${DRIFT_THRESHOLD:-100}"
REPORT_FILE="${REPORT_FILE:-drift-report.txt}"

echo "============================================"
echo "Repo Drift Sweeper - CI Check"
echo "============================================"
echo "Repo: $REPO_ROOT"
echo "Drift threshold: $DRIFT_THRESHOLD"
echo ""

cd "$REPO_ROOT"

# Run the sweeper
if [ "$1" == "--fix" ]; then
    echo "Running in FIX mode..."
    python3 "$SCRIPT_DIR/repo_drift_sweeper.py" --fix --output "$REPORT_FILE"
else
    echo "Running in REPORT mode..."
    python3 "$SCRIPT_DIR/repo_drift_sweeper.py" --output "$REPORT_FILE"
fi

# Count drifts
DRIFT_COUNT=$(grep -c "^\s*[0-9]\+\." "$REPORT_FILE" 2>/dev/null || echo "0")
AUTO_FIXED=$(grep -c "✓" "$REPORT_FILE" 2>/dev/null || echo "0")
FLAGGED=$(grep -c "⚠" "$REPORT_FILE" 2>/dev/null || echo "0")

echo ""
echo "============================================"
echo "Results:"
echo "  Total drifts: $DRIFT_COUNT"
echo "  Auto-fixed: $AUTO_FIXED"
echo "  Flagged for review: $FLAGGED"
echo "  Full report: $REPORT_FILE"
echo "============================================"

# Exit with error if too many drifts
if [ "$DRIFT_COUNT" -gt "$DRIFT_THRESHOLD" ]; then
    echo ""
    echo "ERROR: Drift count ($DRIFT_COUNT) exceeds threshold ($DRIFT_THRESHOLD)"
    echo "Please review and fix drift before merging."
    exit 1
fi

# If there are flagged drifts but no auto-fixable ones, warn but don't fail
if [ "$FLAGGED" -gt 0 ] && [ "$AUTO_FIXED" -eq 0 ]; then
    echo ""
    echo "WARNING: $FLAGGED drifts flagged for manual review."
    echo "Consider running with --fix to auto-fix where possible."
fi

echo ""
echo "Drift check PASSED ✓"
exit 0