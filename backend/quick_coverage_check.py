#!/usr/bin/env python3
"""Quick coverage analysis script"""
import json
import os

def analyze_coverage():
    """Analyze current coverage and identify gaps"""
    coverage_file = 'coverage.json'
    
    if not os.path.exists(coverage_file):
        print("❌ No coverage.json found. Run tests first: python -m pytest --cov=src --cov-report=json")
        return
    
    with open(coverage_file) as f:
        coverage_data = json.load(f)
    
    totals = coverage_data['totals']
    current_coverage = totals['percent_covered']
    covered_lines = totals['covered_lines']
    total_lines = totals['num_statements']
    target_lines = int(total_lines * 0.8)
    needed_lines = target_lines - covered_lines
    
    print("Current Coverage Analysis")
    print(f"   Current: {current_coverage:.1f}% ({covered_lines}/{total_lines} lines)")
    print(f"   Target: 80% ({target_lines} lines)")
    print(f"   Gap: {needed_lines} additional lines needed ({(needed_lines/total_lines)*100:.1f}%)")
    
    # Analyze files by coverage
    files = coverage_data['files']
    high_impact_files = []
    zero_coverage_files = []
    good_coverage_files = []
    
    for file_path, file_data in files.items():
        stmts = file_data['summary']['num_statements']
        covered = file_data['summary']['covered_lines']
        percent = file_data['summary']['percent_covered']
        
        if stmts >= 100:  # High impact files
            if percent == 0:
                zero_coverage_files.append((file_path, stmts))
            elif percent >= 70:
                good_coverage_files.append((file_path, stmts, percent))
            else:
                high_impact_files.append((file_path, stmts, percent, covered))
    
    print("\nHIGH PRIORITY: Zero Coverage Files (100+ statements)")
    zero_coverage_files.sort(key=lambda x: x[1], reverse=True)
    for file_path, stmts in zero_coverage_files[:10]:
        print(f"   {file_path}: {stmts} statements at 0% coverage")
    
    print("\nMEDIUM PRIORITY: Partial Coverage Files (100+ statements)")
    high_impact_files.sort(key=lambda x: (x[2], -x[1]))  # Sort by coverage, then by size
    for file_path, stmts, percent, covered in high_impact_files[:10]:
        potential = int(stmts * 0.7) - covered
        if potential > 0:
            print(f"   {file_path}: {stmts} stmts at {percent:.1f}% (+{potential} potential lines)")
    
    print("\nGOOD COVERAGE: Already Well-Covered Files")
    good_coverage_files.sort(key=lambda x: x[2], reverse=True)
    for file_path, stmts, percent in good_coverage_files[:5]:
        print(f"   {file_path}: {stmts} stmts at {percent:.1f}% coverage")
    
    # Calculate gap analysis
    total_potential = sum([int(stmts * 0.7) for file_path, stmts in zero_coverage_files[:10]])
    print(f"\nSTRATEGIC OPPORTUNITY: Top 10 zero-coverage files could add ~{total_potential} lines")
    print(f"   This would improve overall coverage by {(total_potential/total_lines)*100:.1f}%")
    print(f"   Bringing total from {current_coverage:.1f}% to {current_coverage + (total_potential/total_lines)*100:.1f}%")
    
    return {
        'current_coverage': current_coverage,
        'covered_lines': covered_lines,
        'total_lines': total_lines,
        'needed_lines': needed_lines,
        'zero_coverage_files': zero_coverage_files,
        'high_impact_files': high_impact_files,
        'good_coverage_files': good_coverage_files
    }

if __name__ == "__main__":
    analyze_coverage()
