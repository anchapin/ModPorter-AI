#!/usr/bin/env python3
"""
Quick Coverage Analysis for ModPorter-AI
"""

import json
from pathlib import Path

def analyze_coverage():
    """Analyze current test coverage"""
    coverage_file = Path("coverage.json")
    
    if not coverage_file.exists():
        print("No coverage.json found. Run tests with coverage first:")
        print("  python -m pytest --cov=src --cov-report=json")
        return
    
    with open(coverage_file, 'r') as f:
        data = json.load(f)
    
    total = data.get('totals', {})
    print("=== COVERAGE ANALYSIS ===")
    print(f"Overall coverage: {total.get('percent_covered', 0):.1f}%")
    print(f"Total statements: {total.get('num_statements', 0)}")
    print(f"Covered statements: {total.get('covered_lines', 0)}")
    
    # Find low coverage files
    low_coverage = []
    for file_path, file_data in data.get('files', {}).items():
        coverage = file_data.get('summary', {}).get('percent_covered', 0)
        stmts = file_data.get('summary', {}).get('num_statements', 0)
        
        # Focus on source files with reasonable size
        if ('src/' in file_path and stmts > 50 and coverage < 70):
            low_coverage.append((file_path, coverage, stmts))
    
    low_coverage.sort(key=lambda x: x[1])  # Sort by coverage percentage
    
    print("\n=== HIGH IMPACT FILES FOR COVERAGE IMPROVEMENT ===")
    print("File                                                      Coverage    Statements")
    print("-" * 80)
    
    for file_path, coverage, stmts in low_coverage[:15]:
        print(f"{file_path:57s} {coverage:7.1f}%   {stmts:4d}")
    
    # Calculate potential impact
    if low_coverage:
        total_statements = sum(stmts for _, _, stmts in low_coverage)
        current_coverage = sum(coverage * stmts for coverage, stmts in [(c, s) for _, c, s in low_coverage]) / total_statements
        potential_coverage = sum(80 * stmts for _, _, stmts in low_coverage) / total_statements
        impact = potential_coverage - current_coverage
        
        print("\n=== IMPACT ANALYSIS ===")
        print(f"Files to improve: {len(low_coverage)}")
        print(f"Total statements: {total_statements}")
        print(f"Current average coverage: {current_coverage:.1f}%")
        print("Target average coverage: 80.0%")
        print(f"Potential improvement: +{impact:.1f}% overall")
        
        # Top priority recommendations
        print("\n=== TOP PRIORITY FILES ===")
        for file_path, coverage, stmts in low_coverage[:5]:
            improvement_potential = min(80 - coverage, 50)  # Max 50% improvement realistic
            impact_score = stmts * improvement_potential / 100
            print(f"  {file_path:50s} Impact: {impact_score:.1f} statements")
    
    else:
        print("\nGreat! All high-impact files have good coverage.")

if __name__ == "__main__":
    analyze_coverage()
