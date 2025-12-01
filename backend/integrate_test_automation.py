#!/usr/bin/env python3
"""
Test Automation Integration Script for ModPorter-AI
=================================================

This script integrates all automated test generation tools into a cohesive workflow
that can be used to rapidly achieve 80% test coverage target.

Usage:
    python integrate_test_automation.py --full-workflow
    python integrate_test_automation.py --step coverage-analysis
    python integrate_test_automation.py --step test-generation
    python integrate_test_automation.py --step mutation-testing
    python integrate_test_automation.py --step ci-integration
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List

class TestAutomationIntegrator:
    """Integrates all automation tools into cohesive workflow"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.start_time = time.time()
        self.results = {
            "start_time": self.start_time,
            "steps_completed": [],
            "coverage_before": 0,
            "coverage_after": 0,
            "files_processed": 0,
            "tests_generated": 0,
            "mutation_score": 0,
            "errors": []
        }
    
    def log_step(self, step_name: str, message: str = ""):
        """Log a workflow step"""
        timestamp = time.strftime("%H:%M:%S")
        elapsed = time.time() - self.start_time
        print(f"[{timestamp}] [{elapsed:.1f}s] {step_name}")
        if message:
            print(f"           {message}")
        
        self.results["steps_completed"].append({
            "step": step_name,
            "message": message,
            "timestamp": time.time()
        })
    
    def run_command(self, command: List[str], description: str = "") -> bool:
        """Run a command and return success status"""
        self.log_step(f"Running: {' '.join(command)}", description)
        
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                self.log_step("SUCCESS: Command completed successfully")
                if result.stdout:
                    print(result.stdout[:500])  # Limit output
                return True
            else:
                error_msg = f"Command failed with code {result.returncode}: {result.stderr}"
                self.log_step("FAILED: Command failed", error_msg)
                self.results["errors"].append(error_msg)
                return False
        
        except subprocess.TimeoutExpired:
            error_msg = "Command timed out after 10 minutes"
            self.log_step("TIMEOUT: Command timed out", error_msg)
            self.results["errors"].append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Command execution error: {e}"
            self.log_step("ERROR: Command error", error_msg)
            self.results["errors"].append(error_msg)
            return False
    
    def step_coverage_analysis(self) -> bool:
        """Step 1: Analyze current coverage"""
        self.log_step("STEP 1: COVERAGE ANALYSIS", "Analyzing current test coverage...")
        
        # Run coverage analysis
        success = self.run_command([
            sys.executable, "quick_coverage_analysis.py"
        ], "Analyzing coverage data")
        
        if not success:
            return False
        
        # Get current coverage from coverage.json
        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
            
            coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
            self.results["coverage_before"] = coverage
            
            self.log_step(f"Current coverage: {coverage:.1f}%")
            return True
        else:
            self.log_step("No coverage data found")
            return False
    
    def step_test_generation(self) -> bool:
        """Step 2: Generate automated tests"""
        self.log_step("STEP 2: AUTOMATED TEST GENERATION", "Generating tests for low-coverage files...")
        
        # Use automated test generator to create tests
        success = self.run_command([
            sys.executable, "automated_test_generator.py", 
            "--auto-generate", 
            "--target-coverage", "80"
        ], "Auto-generating tests")
        
        if success:
            # Count generated test files
            tests_dir = self.project_root / "tests"
            if tests_dir.exists():
                test_files = list(tests_dir.glob("test_*.py"))
                recent_tests = [f for f in test_files 
                             if f.stat().st_mtime > self.start_time]
                self.results["tests_generated"] = len(recent_tests)
                self.log_step(f"Generated {len(recent_tests)} new test files")
        
        return success
    
    def step_mutation_testing(self) -> bool:
        """Step 3: Run mutation testing"""
        self.log_step("STEP 3: MUTATION TESTING", "Running mutation testing to identify coverage gaps...")
        
        # Run mutation testing
        success = self.run_command([
            sys.executable, "run_mutation_tests.py"
        ], "Running mutation tests")
        
        if success:
            # Parse mutation results
            results_file = self.project_root / "mutmut-results.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    mutation_data = json.load(f)
                
                mutation_score = mutation_data.get('metadata', {}).get('mutation_score', 0)
                self.results["mutation_score"] = mutation_score
                self.log_step(f"Mutation score: {mutation_score:.1f}%")
        
        return success
    
    def step_coverage_validation(self) -> bool:
        """Step 4: Validate new coverage"""
        self.log_step("STEP 4: COVERAGE VALIDATION", "Running tests and measuring new coverage...")
        
        # Run tests with coverage
        success = self.run_command([
            sys.executable, "-m", "pytest", 
            "--cov=src", 
            "--cov-report=json",
            "--cov-report=term-missing"
        ], "Running tests with coverage")
        
        if success:
            # Get new coverage
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                
                coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                self.results["coverage_after"] = coverage
                
                improvement = coverage - self.results["coverage_before"]
                self.log_step(f"New coverage: {coverage:.1f}% (improvement: +{improvement:.1f}%)")
        
        return success
    
    def step_ci_integration(self) -> bool:
        """Step 5: Create CI/CD integration files"""
        self.log_step("STEP 5: CI/CD INTEGRATION", "Creating GitHub Actions workflow...")
        
        # Create workflow directory
        workflows_dir = self.project_root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test automation workflow
        workflow_content = '''name: Automated Test Generation

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    # Run daily at 2 AM UTC
    - cron: '0 2 * * *'

jobs:
  test-automation:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-test.txt
        pip install pytest-cov mutmut hypothesis
    
    - name: Run coverage analysis
      run: python backend/quick_coverage_analysis.py
    
    - name: Run automated test generation
      run: python backend/automated_test_generator.py --auto-generate --target-coverage 80
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    
    - name: Run tests with coverage
      run: |
        cd backend
        python -m pytest --cov=src --cov-report=json --cov-report=xml
    
    - name: Run mutation testing
      run: |
        cd backend
        python run_mutation_tests.py
      continue-on-error: true
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: Archive test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: |
          backend/coverage.json
          backend/mutmut-results.json
          backend/tests/test_*.py
'''
        
        workflow_file = workflows_dir / "test-automation.yml"
        with open(workflow_file, 'w') as f:
            f.write(workflow_content)
        
        self.log_step(f"Created CI workflow: {workflow_file}")
        return True
    
    def step_summary_report(self) -> bool:
        """Step 6: Generate summary report"""
        self.log_step("STEP 6: SUMMARY REPORT", "Generating automation summary...")
        
        elapsed_time = time.time() - self.start_time
        
        # Create summary report
        report = {
            "workflow_summary": {
                "total_time": elapsed_time,
                "steps_completed": len(self.results["steps_completed"]),
                "success": len(self.results["errors"]) == 0
            },
            "coverage_improvement": {
                "before": self.results["coverage_before"],
                "after": self.results["coverage_after"],
                "improvement": self.results["coverage_after"] - self.results["coverage_before"],
                "target_achieved": self.results["coverage_after"] >= 80.0
            },
            "test_generation": {
                "tests_generated": self.results["tests_generated"],
                "files_processed": self.results["files_processed"]
            },
            "mutation_testing": {
                "mutation_score": self.results["mutation_score"],
                "target_met": self.results["mutation_score"] >= 70.0
            },
            "errors": self.results["errors"]
        }
        
        # Save report
        report_file = self.project_root / "test_automation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.log_step("AUTOMATION WORKFLOW SUMMARY")
        print(f"  Total time: {elapsed_time:.1f} seconds")
        print(f"  Coverage: {self.results['coverage_before']:.1f}% → {self.results['coverage_after']:.1f}% "
              f"(+{self.results['coverage_after'] - self.results['coverage_before']:.1f}%)")
        print(f"  Tests generated: {self.results['tests_generated']}")
        print(f"  Mutation score: {self.results['mutation_score']:.1f}%")
        print(f"  Errors: {len(self.results['errors'])}")
        
        if self.results["coverage_after"] >= 80:
            print("  ✓ 80% COVERAGE TARGET ACHIEVED!")
        else:
            remaining = 80 - self.results["coverage_after"]
            print(f"  ⚠ Need +{remaining:.1f}% more coverage to reach 80% target")
        
        print(f"  Report saved to: {report_file}")
        
        return True
    
    def run_full_workflow(self) -> bool:
        """Run the complete automation workflow"""
        self.log_step("STARTING FULL AUTOMATION WORKFLOW", "Target: 80% test coverage")
        
        steps = [
            ("coverage-analysis", self.step_coverage_analysis),
            ("test-generation", self.step_test_generation),
            ("coverage-validation", self.step_coverage_validation),
            ("mutation-testing", self.step_mutation_testing),
            ("ci-integration", self.step_ci_integration),
            ("summary-report", self.step_summary_report)
        ]
        
        success_count = 0
        for step_name, step_func in steps:
            try:
                if step_func():
                    success_count += 1
                else:
                    self.log_step(f"Step '{step_name}' failed, continuing with workflow...")
            except Exception as e:
                error_msg = f"Step '{step_name}' crashed: {e}"
                self.log_step("✗ Step crashed", error_msg)
                self.results["errors"].append(error_msg)
        
        self.log_step(f"WORKFLOW COMPLETED: {success_count}/{len(steps)} steps successful")
        return success_count == len(steps)


def main():
    """Main function for automation integration"""
    parser = argparse.ArgumentParser(description="Integrate automated test generation workflow")
    parser.add_argument("--full-workflow", action="store_true", 
                       help="Run complete automation workflow")
    parser.add_argument("--step", choices=[
        "coverage-analysis", "test-generation", "mutation-testing", 
        "ci-integration", "summary-report"
    ], help="Run specific workflow step")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    integrator = TestAutomationIntegrator(project_root)
    
    print("=" * 70)
    print("    MODPORTER-AI TEST AUTOMATION INTEGRATION")
    print("=" * 70)
    print()
    
    try:
        if args.full_workflow:
            success = integrator.run_full_workflow()
        elif args.step:
            step_map = {
                "coverage-analysis": integrator.step_coverage_analysis,
                "test-generation": integrator.step_test_generation,
                "mutation-testing": integrator.step_mutation_testing,
                "ci-integration": integrator.step_ci_integration,
                "summary-report": integrator.step_summary_report
            }
            
            if args.step in step_map:
                success = step_map[args.step]()
            else:
                print(f"Unknown step: {args.step}")
                success = False
        else:
            parser.print_help()
            success = True
        
        if success:
            print("\nSUCCESS: Automation integration completed successfully!")
        else:
            print("\nFAILED: Automation integration encountered issues.")
            print("Check the error messages above for details.")
    
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
