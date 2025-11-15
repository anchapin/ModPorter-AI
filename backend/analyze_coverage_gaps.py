"""
Analyze test coverage gaps to identify modules that need more tests.
This script helps identify which modules need more test coverage to reach 80% threshold.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_coverage_data(coverage_file: Path) -> Dict:
    """Load coverage data from JSON file."""
    try:
        with open(coverage_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading coverage file {coverage_file}: {e}")
        return {}


def extract_module_coverage(coverage_data: Dict) -> List[Tuple[str, float, int]]:
    """Extract module coverage information."""
    modules = []
    if 'files' not in coverage_data:
        return modules

    for file_path, file_data in coverage_data['files'].items():
        module_name = file_path.replace('\\', '/')
        # Extract module name from path
        if '/src/' in module_name:
            module_name = module_name.split('/src/')[-1]

        coverage_percent = file_data['summary']['percent_covered']
        missing_lines = file_data['summary']['missing_lines']

        modules.append((module_name, coverage_percent, missing_lines))

    # Sort by coverage percentage (ascending)
    modules.sort(key=lambda x: x[1])
    return modules


def identify_low_coverage_modules(modules: List[Tuple[str, float, int]], threshold: float = 80) -> List[Tuple[str, float, int]]:
    """Identify modules with coverage below threshold."""
    return [m for m in modules if m[1] < threshold]


def generate_report(backend_modules: List[Tuple[str, float, int]],
                   ai_engine_modules: List[Tuple[str, float, int]]) -> str:
    """Generate a coverage gap analysis report."""
    report = ["# Test Coverage Gap Analysis", ""]

    # Backend coverage summary
    backend_total = sum(m[1] for m in backend_modules) / len(backend_modules) if backend_modules else 0
    report.append(f"## Backend Coverage Summary")
    report.append(f"- Overall Coverage: {backend_total:.2f}%")
    report.append(f"- Total Modules: {len(backend_modules)}")
    report.append(f"- Modules Below 80%: {len(identify_low_coverage_modules(backend_modules))}")
    report.append("")

    # Backend low coverage modules
    backend_low = identify_low_coverage_modules(backend_modules)
    report.append("### Backend Modules Needing More Tests")
    for module, coverage, missing in backend_low[:10]:  # Show top 10
        report.append(f"- **{module}**: {coverage:.2f}% coverage, {missing} missing lines")
    report.append("")

    # AI Engine coverage summary
    ai_engine_total = sum(m[1] for m in ai_engine_modules) / len(ai_engine_modules) if ai_engine_modules else 0
    report.append(f"## AI Engine Coverage Summary")
    report.append(f"- Overall Coverage: {ai_engine_total:.2f}%")
    report.append(f"- Total Modules: {len(ai_engine_modules)}")
    report.append(f"- Modules Below 80%: {len(identify_low_coverage_modules(ai_engine_modules))}")
    report.append("")

    # AI Engine low coverage modules
    ai_engine_low = identify_low_coverage_modules(ai_engine_modules)
    report.append("### AI Engine Modules Needing More Tests")
    for module, coverage, missing in ai_engine_low[:10]:  # Show top 10
        report.append(f"- **{module}**: {coverage:.2f}% coverage, {missing} missing lines")
    report.append("")

    # Recommendations
    report.append("## Recommendations")
    report.append("1. Focus on modules with lowest coverage first")
    report.append("2. Add unit tests for uncovered functions and methods")
    report.append("3. Add integration tests for API endpoints")
    report.append("4. Consider test-driven development for new features")
    report.append("5. Set up coverage checks in pull requests")
    report.append("")

    # Priority modules (with critical coverage gaps)
    critical_modules = [
        m for m in backend_low + ai_engine_low
        if m[1] < 40  # Very low coverage threshold
    ]
    if critical_modules:
        report.append("### Critical Modules (Below 40% Coverage)")
        for module, coverage, missing in critical_modules[:5]:  # Show top 5
            report.append(f"- **{module}**: {coverage:.2f}% coverage, {missing} missing lines")

    return "\n".join(report)


def main():
    """Main function to analyze coverage gaps."""
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent

    # Load coverage data
    backend_coverage = load_coverage_data(project_root / "backend" / "coverage.json")
    ai_engine_coverage = load_coverage_data(project_root / "ai-engine" / "coverage.json")

    # Extract module coverage
    backend_modules = extract_module_coverage(backend_coverage)
    ai_engine_modules = extract_module_coverage(ai_engine_coverage)

    # Generate and print report
    report = generate_report(backend_modules, ai_engine_modules)
    print(report)

    # Save report to file
    with open(backend_dir / "coverage_gap_analysis.md", "w") as f:
        f.write(report)

    print(f"\nDetailed report saved to {backend_dir}/coverage_gap_analysis.md")


if __name__ == "__main__":
    main()
