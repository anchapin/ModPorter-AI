#!/usr/bin/env python
"""Quick coverage check script."""

import subprocess
import sys
import json

def run_coverage():
    """Run coverage check and return summary."""
    try:
        # Run pytest with coverage
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "src/tests/unit/",
                "--cov=src",
                "--cov-report=json",
                "--cov-fail-under=0",
                "-q"
            ],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        # Read coverage JSON
        try:
            with open("coverage.json", "r") as f:
                data = json.load(f)
                
            total_coverage = data["totals"]["percent_covered"]
            
            print(f"\n{'='*60}")
            print(f"CURRENT COVERAGE SUMMARY")
            print(f"{'='*60}")
            print(f"Overall Coverage: {total_coverage:.1f}%")
            
            # Find files with lowest coverage
            files = []
            for filename, file_data in data["files"].items():
                if file_data["summary"]["num_statements"] > 0:  # Skip empty files
                    coverage_pct = file_data["summary"]["percent_covered"]
                    files.append((filename, coverage_pct))
            
            # Sort by coverage (lowest first)
            files.sort(key=lambda x: x[1])
            
            print(f"\nTOP 10 FILES NEEDING COVERAGE:")
            for i, (filename, coverage) in enumerate(files[:10], 1):
                print(f"{i:2d}. {filename:<60} {coverage:5.1f}%")
            
            print(f"\nTOP 10 FILES WITH BEST COVERAGE:")
            for i, (filename, coverage) in enumerate(files[-10:][::-1], 1):
                if coverage > 0:
                    print(f"{i:2d}. {filename:<60} {coverage:5.1f}%")
            
            print(f"\n{'='*60}")
            print(f"TARGET: 80.0%")
            print(f"CURRENT: {total_coverage:.1f}%")
            print(f"REMAINING: {80.0 - total_coverage:.1f}%")
            
            return total_coverage
            
        except FileNotFoundError:
            print("Error: coverage.json not found")
            return 0.0
        except json.JSONDecodeError:
            print("Error: Could not parse coverage.json")
            return 0.0
            
    except Exception as e:
        print(f"Error running coverage: {e}")
        return 0.0

if __name__ == "__main__":
    coverage = run_coverage()
    sys.exit(0 if coverage >= 80 else 1)
