"""
Simple test runner for Phase 1 tests.
This script runs all Phase 1 tests and provides a summary of results.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any


def run_tests(module: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Run tests for a specific module.

    Args:
        module: The test module to run
        verbose: Whether to use verbose output

    Returns:
        Dictionary containing test results
    """
    print(f"Running tests for {module}...")

    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)

    # Verify test file exists
    test_file = Path(f"tests/phase1/services/{module}.py")
    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        print(f"Current directory: {os.getcwd()}")
        print("Available files in tests/phase1/services:")
        # Use glob instead of iterdir for better Windows compatibility
        import glob

        files = glob.glob("tests/phase1/services/*.py")
        for file in files:
            print(f"  - {Path(file).name}")
        return {"success": False, "error": "Test file not found"}

    # Build pytest command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        f"tests/phase1/services/{module}.py",
        "--tb=short",
        "-q",  # Quiet output for cleaner summary
    ]

    if verbose:
        cmd.append("-v")

    # Run tests
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5-minute timeout
        )

        # Parse output for test statistics
        output_lines = result.stdout.split("\n")

        # Look for test summary line
        summary_line = None
        for line in output_lines:
            if "passed" in line and ("failed" in line or "error" in line):
                summary_line = line
                break

        # Extract test statistics
        tests_run = 0
        failures = 0
        errors = 0

        if summary_line:
            parts = summary_line.split()
            for i, part in enumerate(parts):
                if part.isdigit() and i < len(parts) - 1:
                    tests_run = int(part)
                elif part in ["failed", "error"] and i > 0 and parts[i - 1].isdigit():
                    failures = int(parts[i - 1])

        success = result.returncode == 0 and failures == 0

        return {
            "success": success,
            "tests_run": tests_run,
            "failures": failures,
            "errors": errors,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cmd": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        print(f"Tests for {module} timed out")
        return {
            "success": False,
            "tests_run": 0,
            "failures": 0,
            "errors": 1,
            "stdout": "",
            "stderr": "Test execution timed out",
            "cmd": " ".join(cmd),
        }
    except Exception as e:
        print(f"Error running tests for {module}: {e}")
        return {
            "success": False,
            "tests_run": 0,
            "failures": 0,
            "errors": 1,
            "stdout": "",
            "stderr": str(e),
            "cmd": " ".join(cmd),
        }


def main():
    """Main function to run tests."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Phase 1 tests for ModPorter-AI backend"
    )
    parser.add_argument("--module", type=str, help="Run a specific test module")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Test modules
    test_modules = [
        "test_simple",
        "test_conversion_inference",
        "test_knowledge_graph_crud",
        "test_version_compatibility",
        "test_batch_processing",
        "test_cache",
    ]

    if args.module and args.module in test_modules:
        # Run a specific module
        result = run_tests(args.module, args.verbose)
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(
            f"\n{args.module}: {status} ({result['tests_run']} tests, {result['failures']} failures)"
        )

        if not result["success"] and result["stderr"]:
            print(f"STDERR: {result['stderr']}")

        sys.exit(0 if result["success"] else 1)

    # Run all modules
    print("=" * 60)
    print("PHASE 1 SERVICE TESTS - MODPORTER-AI")
    print("=" * 60)

    all_results = {}
    total_tests = 0
    total_failures = 0

    for module in test_modules:
        result = run_tests(module, args.verbose)
        all_results[module] = result

        total_tests += result["tests_run"]
        total_failures += result["failures"] + result["errors"]

        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(
            f"{module}: {status} ({result['tests_run']} tests, {result['failures']} failures)"
        )

    # Print summary
    total_passed = total_tests - total_failures
    success_rate = 100 * total_passed / max(total_tests, 1)

    print("\n" + "=" * 60)
    print("PHASE 1 TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failures}")
    print(f"Success rate: {success_rate:.1f}%")

    overall_success = all(result["success"] for result in all_results.values())

    print("\n" + "=" * 60)
    if overall_success:
        print("🎉 ALL PHASE 1 TESTS PASSED! 🎉")
    else:
        print("❌ SOME PHASE 1 TESTS FAILED ❌")
    print("=" * 60)

    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()
