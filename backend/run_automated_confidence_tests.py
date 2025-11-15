#!/usr/bin/env python3
"""
Test runner for automated_confidence_scoring tests.
This script runs the tests and provides detailed output.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run the automated_confidence_scoring tests."""
    # Get the backend directory
    backend_dir = Path(__file__).parent

    # Change to the backend directory
    os.chdir(backend_dir)

    # Run the tests
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/test_automated_confidence_scoring.py",
            "-v", "--tb=short", "-x"
        ], capture_output=True, text=True)

        # Print the output
        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"Return code: {result.returncode}")

        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
