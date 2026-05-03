#!/bin/bash
# Automated test runner with intelligent splitting
# Usage: ./auto-test.sh [mode] [coverage-target]

set -e

MODE="${1:-unit}"
COVERAGE_TARGET="${2:-80}"

BACKEND_DIR="backend"

echo "🧪 ModPorter-AI Automated Test Runner"
echo "======================================="
echo "Mode: $MODE"
echo "Coverage Target: ${COVERAGE_TARGET}%"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0
SKIPPED=0

run_tests() {
    local description="$1"
    local cmd="$2"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 $description"
    echo "Command: $cmd"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if eval "$cmd"; then
        echo -e "${GREEN}✅ $description: PASSED${NC}"
        PASSED=$((PASSED+1))
        return 0
    else
        echo -e "${RED}❌ $description: FAILED${NC}"
        FAILED=$((FAILED+1))
        return 1
    fi
}

case "$MODE" in
    unit)
        echo "📁 Running unit tests with coverage..."
        run_tests "Unit Tests (with coverage)" \
            "cd $BACKEND_DIR && python3 -m pytest src/tests/unit/ --cov=src --cov-fail-under=$COVERAGE_TARGET -q --tb=short"
        ;;
    
    unit-fast)
        echo "⚡ Running fast unit tests (no coverage)..."
        run_tests "Unit Tests (fast)" \
            "cd $BACKEND_DIR && python3 -m pytest src/tests/unit/ -q --tb=no --ignore=src/tests/unit/test_task_worker_coverage.py"
        ;;
    
    integration)
        echo "🔗 Running integration tests..."
        run_tests "Integration Tests" \
            "cd $BACKEND_DIR && python3 -m pytest src/tests/integration/ -v --tb=short"
        ;;
    
    full)
        echo "🚀 Running full test suite..."
        
        # Fast unit tests first
        run_tests "Unit Tests (fast)" \
            "cd $BACKEND_DIR && python3 -m pytest src/tests/unit/ -q --tb=no --ignore=src/tests/unit/test_task_worker_coverage.py"
        
        # Coverage tests second
        run_tests "Unit Tests (coverage)" \
            "cd $BACKEND_DIR && python3 -m pytest src/tests/unit/ --cov=src --cov-fail-under=$COVERAGE_TARGET -q --tb=short --ignore=src/tests/unit/test_task_worker_coverage.py"
        
        # Integration tests third
        run_tests "Integration Tests" \
            "cd $BACKEND_DIR && python3 -m pytest src/tests/integration/ -v --tb=short"
        ;;
    
    split)
        echo "📊 Running split test batches (for CI)..."
        
        echo "Batch 1: a-c* tests"
        run_tests "Tests (a-c*)" \
            "cd $BACKEND_DIR && python3 -m pytest src/tests/unit/test_a*.py src/tests/unit/test_b*.py src/tests/unit/test_c*.py -q --tb=no 2>/dev/null || true"
        
        echo "Batch 2: d-m* tests"
        run_tests "Tests (d-m*)" \
            "cd $BACKEND_DIR && python3 -m pytest src/tests/unit/test_d*.py src/tests/unit/test_e*.py src/tests/unit/test_f*.py src/tests/unit/test_g*.py src/tests/unit/test_h*.py src/tests/unit/test_i*.py src/tests/unit/test_j*.py src/tests/unit/test_k*.py src/tests/unit/test_l*.py src/tests/unit/test_m*.py -q --tb=no 2>/dev/null || true"
        
        echo "Batch 3: n-z* tests"
        run_tests "Tests (n-z*)" \
            "cd $BACKEND_DIR && python3 -m pytest src/tests/unit/test_n*.py src/tests/unit/test_o*.py src/tests/unit/test_p*.py src/tests/unit/test_q*.py src/tests/unit/test_r*.py src/tests/unit/test_s*.py src/tests/unit/test_t*.py src/tests/unit/test_u*.py src/tests/unit/test_v*.py src/tests/unit/test_w*.py src/tests/unit/test_x*.py src/tests/unit/test_y*.py src/tests/unit/test_z*.py -q --tb=no 2>/dev/null || true"
        ;;
    
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Usage: $0 [unit|unit-fast|integration|full|split] [coverage-target]"
        exit 1
        ;;
esac

echo ""
echo "======================================="
echo "📊 Test Summary"
echo "======================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All test batches passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some test batches failed${NC}"
    exit 1
fi
