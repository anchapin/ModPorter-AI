#!/bin/bash
# pre-commit hook for ModPorter-AI
# Run automated quality gates before commit
# Usage: Run via git hooks or manually

set -e

echo "🔍 Running pre-commit quality gates..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

# Gate 1: Ruff format check
echo "📝 Checking code format..."
if ! python3 -m ruff format --check . 2>/dev/null; then
    echo -e "${RED}❌ Format check failed. Run: ruff format ." >&2
    FAILURES=$((FAILURES+1))
else
    echo -e "${GREEN}✓ Format check passed"
fi

# Gate 2: Ruff lint check
echo "🔎 Running lint check..."
if ! python3 -m ruff check . 2>/dev/null; then
    echo -e "${RED}❌ Lint check failed. Fix issues or use --fix" >&2
    FAILURES=$((FAILURES+1))
else
    echo -e "${GREEN}✓ Lint check passed"
fi

# Gate 3: Bandit security scan
echo "🔒 Running security scan..."
if command -v bandit &> /dev/null; then
    if ! bandit -r backend/src -f json -o /tmp/bandit.json 2>/dev/null; then
        echo -e "${RED}❌ Security issues found. Review /tmp/bandit.json" >&2
        FAILURES=$((FAILURES+1))
    else
        echo -e "${GREEN}✓ Security scan passed"
    fi
else
    echo -e "${YELLOW}⚠ bandit not installed, skipping"
fi

# Gate 4: Secrets detection (gitleaks)
echo "🔐 Checking for secrets..."
if command -v gitleaks &> /dev/null; then
    if gitleaks detect --source . --redact 2>/dev/null; then
        echo -e "${GREEN}✓ No secrets detected"
    else
        echo -e "${RED}❌ Secrets detected. Review and remove before committing" >&2
        FAILURES=$((FAILURES+1))
    fi
else
    echo -e "${YELLOW}⚠ gitleaks not installed, skipping"
fi

# Gate 5: Fast unit test check
echo "⚡ Running quick unit tests..."
cd backend
if python3 -m pytest src/tests/unit/ -q --tb=no -x 2>/dev/null; then
    echo -e "${GREEN}✓ Quick tests passed"
else
    echo -e "${RED}❌ Unit tests failed" >&2
    FAILURES=$((FAILURES+1))
fi
cd ..

# Final result
echo ""
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All pre-commit checks passed!"
    exit 0
else
    echo -e "${RED}❌ $FAILURES pre-commit check(s) failed"
    echo -e "${YELLOW}Fix issues before committing"
    exit 1
fi
