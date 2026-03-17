#!/bin/bash
# Test script to validate act CLI local CI execution
# Verifies that GitHub Actions workflows can be executed locally

set -e

echo "Testing act CLI Local CI Execution"
echo "==================================="
echo ""

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo "❌ act CLI is not installed. Install from: https://github.com/nektos/act"
    exit 1
fi

echo "✅ act CLI found: $(act --version)"
echo ""

# Validate all workflows can be listed
echo "📋 Validating workflow syntax..."
if act --list > /tmp/act-list.txt 2>&1; then
    echo "✅ All workflows validated successfully"
    echo ""
    
    # Show available workflows
    echo "Available workflows for local execution:"
    grep "docker-publish.yml" /tmp/act-list.txt && echo "  ✅ docker-publish.yml: Ready"
    
else
    echo "❌ Workflow validation failed"
    cat /tmp/act-list.txt
    exit 1
fi

echo ""
echo "Testing specific workflow: Docker Publish"
echo "----------------------------------------"

# Test the docker-publish workflow (release event)
if act release --list 2>&1 | grep -q "build-and-push"; then
    echo "✅ docker-publish.yml is valid for 'release' event"
else
    echo "❌ docker-publish.yml failed validation"
    exit 1
fi

echo ""
echo "✅ All act CLI validation tests passed!"
echo ""
echo "To run a workflow locally:"
echo "  act release                           # Run docker-publish on release event"
echo "  act pull_request                      # Run CI workflow on PR"
echo "  act push                              # Run CI workflow on push"
echo ""
