"""
Test runner for Phase 1 service tests.

This module provides a comprehensive test runner for the Phase 1 services:
- ConversionInferenceEngine
- KnowledgeGraphCRUD
- VersionCompatibilityService
- BatchProcessingService
- CacheService

The test runner executes all test suites and provides a summary of results.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

class Phase1TestRunner:
    """Test runner for Phase 1 services."""

    def __init__(self):
        self.test_modules = [
            "test_conversion_inference",
            "test_knowledge_graph_crud",
            "test_version_compatibility",
            "test_batch_processing",
            "test_cache"
        ]
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_all_tests(self, coverage: bool = True, verbose: bool = False) -> Dict[str, Any]:
        """
        Run all Phase 1 tests.

        Args:
            coverage: Whether to generate coverage reports
            verbose: Whether to use verbose output

        Returns:
            Dictionary containing test results and statistics
        """
        print("=" * 60)
        print("PHASE 1 SERVICE TESTS - MODPORTER-AI")
        print("=" * 60)
        print("Testing services:")
        for module in self.test_modules:
            print(f"  - {module}")
        print("=" * 60)

        self.start_time = time.time()

        # Change to the backend directory
        backend_dir = Path(__file__).parent.parent
        os.chdir(backend_dir)

        # Run tests for each module
        for module in self.test_modules:
            module_result = self.run_test_module(module, coverage, verbose)
            self.results[module] = module_result

            # Print intermediate results
            status = "✅ PASSED" if module_result["success"] else "❌ FAILED"
            print(f"{module}: {status} ({module_result['tests_run']} tests, {module_result['failures']} failures)")

        self.end_time = time.time()

        # Generate final summary
        return self.generate_summary(coverage)

    def run_test_module(self, module: str, coverage: bool, verbose: bool) -> Dict[str, Any]:
        """
        Run tests for a specific module.

        Args:
            module: The test module to run
            coverage: Whether to generate coverage reports
            verbose: Whether to use verbose output

        Returns:
            Dictionary containing test results for the module
        """
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            f"tests/phase1/services/{module}.py",
            "--tb=short"
        ]

        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend([
                f"--cov=src/services/{module.replace('test_', '')}",
                "--cov-report=term-missing",
                "--cov-report=html",
                f"--cov-report=html:htmlcov_{module}"
            ])

        # Run the tests
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5-minute timeout
            )

            # Parse output
            output_lines = result.stdout.split("\n")
            summary_lines = [line for line in output_lines if "=" in line and ("passed" in line or "failed" in line)]

            # Extract test statistics
            tests_run = 0
            failures = 0
            errors = 0

            for line in summary_lines:
                if "passed" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit() and i+1 < len(parts):
                            tests_run = int(part)
                            break

                if "failed" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit() and i+1 < len(parts):
                            failures = int(part)
                            break

                if "error" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit() and i+1 < len(parts):
                            errors = int(part)
                            break

            return {
                "success": result.returncode == 0,
                "tests_run": tests_run,
                "failures": failures,
                "errors": errors,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "cmd": " ".join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "tests_run": 0,
                "failures": 0,
                "errors": 1,
                "stdout": "",
                "stderr": "Test execution timed out",
                "cmd": " ".join(cmd)
            }

    def generate_summary(self, coverage: bool) -> Dict[str, Any]:
        """
        Generate a summary of all test results.

        Args:
            coverage: Whether coverage reports were generated

        Returns:
            Dictionary containing the test summary
        """
        total_tests = sum(result["tests_run"] for result in self.results.values())
        total_failures = sum(result["failures"] + result["errors"] for result in self.results.values())
        total_passed = total_tests - total_failures

        successful_modules = sum(1 for result in self.results.values() if result["success"])
        total_modules = len(self.results)

        duration = self.end_time - self.start_time

        print("\n" + "=" * 60)
        print("PHASE 1 TEST SUMMARY")
        print("=" * 60)
        print(f"Total modules tested: {successful_modules}/{total_modules}")
        print(f"Total tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failures}")
        print(f"Success rate: {100 * total_passed / max(total_tests, 1):.1f}%")
        print(f"Duration: {duration:.1f} seconds")

        # Detailed results
        print("\nDETAILED RESULTS:")
        print("-" * 60)
        for module, result in self.results.items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"{module}: {status}")
            print(f"  Tests run: {result['tests_run']}")
            print(f"  Failures: {result['failures']}")
            print(f"  Errors: {result['errors']}")

        # Overall result
        overall_success = all(result["success"] for result in self.results.values())
        print("\n" + "=" * 60)
        if overall_success:
            print("🎉 ALL PHASE 1 TESTS PASSED! 🎉")
        else:
            print("❌ SOME PHASE 1 TESTS FAILED ❌")
        print("=" * 60)

        # Coverage reports
        if coverage:
            print("\nCoverage reports generated:")
            for module in self.test_modules:
                html_file = f"htmlcov_{module}/index.html"
                if os.path.exists(html_file):
                    print(f"  - {module}: {html_file}")

        return {
            "overall_success": overall_success,
            "modules_tested": total_modules,
            "modules_passed": successful_modules,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failures": total_failures,
            "success_rate": 100 * total_passed / max(total_tests, 1),
            "duration": duration,
            "results": self.results
        }

    def run_specific_module(self, module: str, coverage: bool = True, verbose: bool = False) -> Dict[str, Any]:
        """
        Run tests for a specific module.

        Args:
            module: The test module to run
            coverage: Whether to generate coverage reports
            verbose: Whether to use verbose output

        Returns:
            Dictionary containing test results for the module
        """
        if module not in self.test_modules:
            print(f"Error: Module '{module}' not found in Phase 1 tests")
            return {"success": False, "error": "Module not found"}

        print("=" * 60)
        print(f"PHASE 1 TESTS - {module.upper()}")
        print("=" * 60)

        self.start_time = time.time()

        # Change to the backend directory
        backend_dir = Path(__file__).parent.parent
        os.chdir(backend_dir)

        # Run the tests
        result = self.run_test_module(module, coverage, verbose)
        self.results[module] = result

        # Print results
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{module}: {status} ({result['tests_run']} tests, {result['failures']} failures)")

        if not result["success"] and result["stderr"]:
            print("\nSTDERR:")
            print(result["stderr"])

        if not result["success"] and result["stdout"]:
            # Extract failed test details
            output_lines = result["stdout"].split("\n")
            failed_sections = []
            in_failed_section = False
            current_section = []

            for line in output_lines:
                if line.startswith("____") and "FAILED" in line:
                    in_failed_section = True
                    current_section = [line]
                elif in_failed_section and line.startswith("____"):
                    in_failed_section = False
                    failed_sections.append("\n".join(current_section))
                elif in_failed_section:
                    current_section.append(line)

            if failed_sections:
                print("\nFAILED TESTS:")
                for section in failed_sections:
                    print(section)

        self.end_time = time.time()

        print(f"\nDuration: {self.end_time - self.start_time:.1f} seconds")

        # Coverage report
        if coverage and result["success"]:
            html_file = f"htmlcov_{module}/index.html"
            if os.path.exists(html_file):
                print(f"Coverage report: {html_file}")

        return result


def main():
    """Main function to run tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Phase 1 tests for ModPorter-AI backend")
    parser.add_argument("--module", type=str, help="Run a specific test module")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    runner = Phase1TestRunner()

    if args.module:
        # Run a specific module
        result = runner.run_specific_module(
            args.module,
            coverage=not args.no_coverage,
            verbose=args.verbose
        )
        sys.exit(0 if result["success"] else 1)
    else:
        # Run all modules
        result = runner.run_all_tests(
            coverage=not args.no_coverage,
            verbose=args.verbose
        )
        sys.exit(0 if result["overall_success"] else 1)


if __name__ == "__main__":
    main()
