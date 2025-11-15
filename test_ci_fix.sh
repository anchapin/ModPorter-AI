#!/bin/bash

# Test script to verify CI fix
echo "Testing CI fix for test collection errors..."

# Set up environment
cd "$(dirname "$0")"
export PYTHONPATH=backend/src:$PYTHONPATH

# Try to collect tests from backend
echo "Collecting backend tests..."
python -m pytest backend/tests/ --collect-only -q 2>&1 | grep -E "(ERROR|FAILED|collected)"

# Try to collect just a few specific tests
echo "Collecting specific failing tests..."
python -m pytest backend/tests/test_assets_api.py backend/tests/test_behavior_export_api.py backend/tests/test_caching_api.py --collect-only -q 2>&1 | grep -E "(ERROR|FAILED|collected)"

echo "CI fix test completed."
