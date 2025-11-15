"""
Test runner script for service-specific tests with coverage reporting.

This script allows running tests for individual services (backend, ai-engine, frontend)
with detailed coverage reports. It's designed to help identify areas where test coverage
can be improved and to track progress over time.
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ServiceTestRunner:
    """Handles running tests for specific services with coverage."""

    def __init__(self, project_root: Path):
        """Initialize the test runner."""
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.ai_engine_dir = project_root / "ai-engine"
        self.frontend_dir = project_root / "frontend"

    def run_backend_tests(
        self,
        module: Optional[str] = None,
        coverage_report: bool = True,
        html_report: bool = True,
        verbose: bool = True,
        fail_under: float = 80.0
    ) -> Tuple[int, Dict]:
        """
        Run backend tests with optional coverage reporting.

        Args:
            module: Specific module to test (e.g., "services.cache")
            coverage_report: Whether to generate coverage report
            html_report: Whether to generate HTML coverage report
            verbose: Whether to run tests in verbose mode
            fail_under: Minimum coverage percentage for tests to pass

        Returns:
            Tuple of exit code and results dictionary
        """
        # Change to backend directory
        os.chdir(self.backend_dir)

        # Build pytest command
        cmd = ["python", "-m", "pytest"]

        # Add module path if specified
        if module:
            test_path = f"tests/unit/services/test_{module}.py"
            if not os.path.exists(test_path):
                # Try other possible paths
                test_path = f"tests/{module}/"
                if not os.path.exists(test_path):
                    test_path = f"tests/test_{module}.py"
            if os.path.exists(test_path):
                cmd.append(test_path)
            else:
                print(f"Warning: Test path {test_path} not found, running all tests")
                cmd.append("tests")
        else:
            cmd.append("tests")

        # Add verbose flag
        if verbose:
            cmd.append("-v")

        # Add coverage options if requested
        if coverage_report:
            cmd.extend([
                "--cov=src",
                f"--cov-fail-under={fail_under}"
            ])

            if html_report:
                cmd.extend(["--cov-report=html:htmlcov"])

            cmd.extend([
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json"
            ])

        # Set up environment variables
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.backend_dir / "src")
        env["TESTING"] = "true"
        env["DISABLE_REDIS"] = "true"  # Use mock Redis
        env["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

        print(f"Running command: {' '.join(cmd)}")
        print(f"Working directory: {os.getcwd()}")

        # Run tests
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        # Parse results
        test_results = self._parse_test_results(result, "backend")

        return result.returncode, test_results

    def run_ai_engine_tests(
        self,
        module: Optional[str] = None,
        coverage_report: bool = True,
        html_report: bool = True,
        verbose: bool = True,
        fail_under: float = 80.0
    ) -> Tuple[int, Dict]:
        """
        Run AI engine tests with optional coverage reporting.

        Args:
            module: Specific module to test
            coverage_report: Whether to generate coverage report
            html_report: Whether to generate HTML coverage report
            verbose: Whether to run tests in verbose mode
            fail_under: Minimum coverage percentage for tests to pass

        Returns:
            Tuple of exit code and results dictionary
        """
        # Change to ai-engine directory
        os.chdir(self.ai_engine_dir)

        # Build pytest command
        cmd = ["python", "-m", "pytest"]

        # Add module path if specified
        if module:
            test_path = f"tests/unit/{module}/"
            if not os.path.exists(test_path):
                test_path = f"tests/integration/{module}/"
            if not os.path.exists(test_path):
                test_path = f"tests/test_{module}.py"
            if os.path.exists(test_path):
                cmd.append(test_path)
            else:
                print(f"Warning: Test path {test_path} not found, running all tests")
                cmd.append("tests")
        else:
            cmd.append("tests")

        # Add verbose flag
        if verbose:
            cmd.append("-v")

        # Add coverage options if requested
        if coverage_report:
            cmd.extend([
                "--cov=src",
                f"--cov-fail-under={fail_under}"
            ])

            if html_report:
                cmd.extend(["--cov-report=html:htmlcov"])

            cmd.extend([
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json"
            ])

        # Set up environment variables
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.ai_engine_dir / "src")
        env["TESTING"] = "true"
        env["USE_MOCK_LLM"] = "true"  # Use mock LLM for tests

        print(f"Running command: {' '.join(cmd)}")
        print(f"Working directory: {os.getcwd()}")

        # Run tests
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        # Parse results
        test_results = self._parse_test_results(result, "ai-engine")

        return result.returncode, test_results

    def run_frontend_tests(
        self,
        component: Optional[str] = None,
        coverage_report: bool = True,
        watch: bool = False
    ) -> Tuple[int, Dict]:
        """
        Run frontend tests with pnpm.

        Args:
            component: Specific component to test
            coverage_report: Whether to generate coverage report
            watch: Whether to run tests in watch mode

        Returns:
            Tuple of exit code and results dictionary
        """
        # Change to frontend directory
        os.chdir(self.frontend_dir)

        # Build test command
        cmd = ["pnpm", "test"]

        # Add coverage flag if requested
        if coverage_report and not watch:
            cmd.append("--coverage")

        # Add component filter if specified
        if component:
            cmd.append("--")
            cmd.append(f"--testNamePattern={component}")

        # Add watch flag if requested
        if watch:
            cmd.append("--watch")

        print(f"Running command: {' '.join(cmd)}")
        print(f"Working directory: {os.getcwd()}")

        # Run tests
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse results (simplified for frontend)
        test_results = {
            "service": "frontend",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

        # Try to extract coverage from stdout if available
        if coverage_report and result.returncode == 0:
            try:
                # Look for coverage percentage in output
                import re
                coverage_match = re.search(r"All files\s+\|\s+(\d+\.?\d*)", result.stdout)
                if coverage_match:
                    test_results["coverage_percent"] = float(coverage_match.group(1))
            except Exception:
                pass

        return result.returncode, test_results

    def _parse_test_results(self, result: subprocess.CompletedProcess, service: str) -> Dict:
        """Parse test results from subprocess output."""
        test_results = {
            "service": service,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

        # Try to extract test count from output
        try:
            import re

            # Look for test summary
            summary_match = re.search(r"(\d+)\s+passed\s+(\d+)\s+failed", result.stdout)
            if summary_match:
                test_results["passed"] = int(summary_match.group(1))
                test_results["failed"] = int(summary_match.group(2))

            # Try to parse coverage from JSON report if it exists
            coverage_path = os.path.join(os.getcwd(), "coverage.json")
            if os.path.exists(coverage_path):
                with open(coverage_path, "r") as f:
                    coverage_data = json.load(f)
                    test_results["coverage_percent"] = coverage_data["totals"]["percent_covered"]
                    test_results["coverage_lines_covered"] = coverage_data["totals"]["covered_lines"]
                    test_results["coverage_lines_missing"] = coverage_data["totals"]["missing_lines"]
        except Exception:
            pass

        return test_results

    def generate_coverage_report(self, results: List[Dict], output_file: str = "coverage_report.json"):
        """Generate a combined coverage report from test results."""
        report = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "services": results
        }

        # Write report to file
        report_path = self.project_root / output_file
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Coverage report saved to: {report_path}")

        # Print summary
        print("\n=== Test Coverage Summary ===")
        for result in results:
            service = result.get("service", "unknown")
            exit_code = result.get("exit_code", -1)
            status = "PASS" if exit_code == 0 else "FAIL"

            if "coverage_percent" in result:
                coverage = result["coverage_percent"]
                passed = result.get("passed", "N/A")
                failed = result.get("failed", "N/A")
                print(f"{service}: {status} - Coverage: {coverage:.1f}% - Tests: {passed} passed, {failed} failed")
            else:
                print(f"{service}: {status}")


def main():
    """Main entry point for the test runner script."""
    parser = argparse.ArgumentParser(
        description="Run service-specific tests with coverage reporting"
    )

    parser.add_argument(
        "--service",
        choices=["backend", "ai-engine", "frontend", "all"],
        default="all",
        help="Service to test"
    )

    parser.add_argument(
        "--module",
        help="Specific module to test (backend and ai-engine only)"
    )

    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )

    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Disable HTML coverage report"
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Run tests in quiet mode"
    )

    parser.add_argument(
        "--fail-under",
        type=float,
        default=80.0,
        help="Minimum coverage percentage for tests to pass"
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run tests in watch mode (frontend only)"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = ServiceTestRunner(project_root)

    # Store all results
    all_results = []

    # Determine which services to test
    services_to_test = []
    if args.service == "all":
        services_to_test = ["backend", "ai-engine", "frontend"]
    else:
        services_to_test = [args.service]

    # Run tests for each service
    for service in services_to_test:
        print(f"\n{'='*50}")
        print(f"Running tests for {service} service")
        print(f"{'='*50}\n")

        if service == "backend":
            exit_code, results = runner.run_backend_tests(
                module=args.module,
                coverage_report=not args.no_coverage,
                html_report=not args.no_html,
                verbose=not args.quiet,
                fail_under=args.fail_under
            )
        elif service == "ai-engine":
            exit_code, results = runner.run_ai_engine_tests(
                module=args.module,
                coverage_report=not args.no_coverage,
                html_report=not args.no_html,
                verbose=not args.quiet,
                fail_under=args.fail_under
            )
        elif service == "frontend":
            exit_code, results = runner.run_frontend_tests(
                component=args.module,
                coverage_report=not args.no_coverage,
                watch=args.watch
            )

        all_results.append(results)

        if exit_code != 0:
            print(f"\n❌ Tests for {service} failed with exit code {exit_code}")
            if not args.quiet and "stderr" in results and results["stderr"]:
                print("\nSTDERR:")
                print(results["stderr"])
        else:
            print(f"\n✅ All tests for {service} passed")

    # Generate combined report
    if len(all_results) > 0:
        runner.generate_coverage_report(all_results)

    # Return appropriate exit code
    failed_services = [r for r in all_results if r.get("exit_code", -1) != 0]
    return 1 if failed_services else 0


if __name__ == "__main__":
    sys.exit(main())
